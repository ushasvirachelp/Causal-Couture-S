import pandas as pd


def build_causal_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a Phase 5 causal-analysis dataset from the unified date × SKU dataset.

    The first causal question examines whether social engagement at time t
    affects product sales at time t+1.

    This function creates lagged and lead variables within each SKU so that
    temporal relationships are preserved correctly.
    """

    if df.empty:
        return df.copy()

    causal_df = df.copy()

    required_columns = {
        "date",
        "sku_id",
        "units_sold",
        "engagement_rate",
    }

    missing = required_columns - set(causal_df.columns)

    if missing:
        raise ValueError(
            f"Cannot build causal dataset. Missing required columns: {sorted(missing)}"
        )

    # Normalize date
    causal_df["date"] = pd.to_datetime(
        causal_df["date"],
        errors="coerce",
    )

    # Ensure important numeric variables are numeric
    numeric_columns = [
        "units_sold",
        "engagement_rate",
        "closing_stock",
        "product_views",
        "view_to_cart_rate",
    ]

    for column in numeric_columns:
        if column in causal_df.columns:
            causal_df[column] = pd.to_numeric(
                causal_df[column],
                errors="coerce",
            )

    # Remove rows that cannot participate in temporal analysis
    causal_df = causal_df.dropna(
        subset=[
            "date",
            "sku_id",
            "units_sold",
            "engagement_rate",
        ]
    )

    # Temporal calculations must occur within each SKU
    causal_df = causal_df.sort_values(
        ["sku_id", "date"]
    ).reset_index(drop=True)

    grouped = causal_df.groupby("sku_id", group_keys=False)

    # Current-period variables
    causal_df["engagement_rate_t"] = causal_df["engagement_rate"]
    causal_df["units_sold_t"] = causal_df["units_sold"]

    if "closing_stock" in causal_df.columns:
        causal_df["closing_stock_t"] = causal_df["closing_stock"]

    if "product_views" in causal_df.columns:
        causal_df["product_views_t"] = causal_df["product_views"]

    if "view_to_cart_rate" in causal_df.columns:
        causal_df["view_to_cart_rate_t"] = causal_df["view_to_cart_rate"]

    # Prior-period variables
    causal_df["engagement_rate_lag1"] = (
        grouped["engagement_rate"].shift(1)
    )

    causal_df["units_sold_lag1"] = (
        grouped["units_sold"].shift(1)
    )

    # Primary Phase 5 outcome:
    # engagement today -> units sold tomorrow
    causal_df["next_observed_date"] = (
    grouped["date"].shift(-1)
)

    causal_df["units_sold_next_observation"] = (
    grouped["units_sold"].shift(-1)
)

    causal_df["days_to_next_observation"] = (
    causal_df["next_observed_date"] - causal_df["date"]
).dt.days

    causal_df["units_sold_next_day"] = (
    causal_df["units_sold_next_observation"]
    .where(
        causal_df["days_to_next_observation"] == 1
    )
)

    # Flag whether inventory could constrain observed demand
    if "closing_stock" in causal_df.columns:
        causal_df["inventory_constrained_flag"] = (
            causal_df["closing_stock"].fillna(0) <= 0
        ).astype(int)

    # A valid row for the first causal model needs:
    # treatment, outcome, and prior-demand information
    causal_df["causal_row_valid"] = (
        causal_df[
            [
                "engagement_rate_t",
                "units_sold_next_day",
                "units_sold_lag1",
            ]
        ]
        .notna()
        .all(axis=1)
        .astype(int)
    )

    return causal_df


def get_causal_dataset_summary(df: pd.DataFrame) -> dict:
    """
    Return a small diagnostic summary for the causal-analysis dataset.
    """

    if df.empty:
        return {
            "rows": 0,
            "valid_causal_rows": 0,
            "unique_skus": 0,
        }

    summary = {
        "rows": int(len(df)),
        "valid_causal_rows": int(
            df["causal_row_valid"].sum()
            if "causal_row_valid" in df.columns
            else 0
        ),
        "unique_skus": int(
            df["sku_id"].nunique()
            if "sku_id" in df.columns
            else 0
        ),
    }

    if "inventory_constrained_flag" in df.columns:
        summary["inventory_constrained_rows"] = int(
            df["inventory_constrained_flag"].sum()
        )

    return summary