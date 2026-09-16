import pandas as pd


def analyze_stockout_bias(df: pd.DataFrame) -> dict:
    """
    Diagnose whether observed sales may be suppressed by limited inventory.

    Important:
    This does NOT estimate latent demand.
    It identifies observations where units_sold may not represent
    true customer demand because inventory availability was limited.
    """

    if df.empty:
        return {
            "status": "insufficient_data",
            "rows": 0,
        }

    stock_df = df.copy()

    if "closing_stock_t" not in stock_df.columns:
        return {
            "status": "inventory_data_unavailable",
            "rows": int(len(stock_df)),
            "message": (
                "closing_stock_t is not available, so stockout "
                "bias cannot be evaluated."
            ),
        }

    stock_df["closing_stock_t"] = pd.to_numeric(
        stock_df["closing_stock_t"],
        errors="coerce",
    )

    if "units_sold_t" in stock_df.columns:
        stock_df["units_sold_t"] = pd.to_numeric(
            stock_df["units_sold_t"],
            errors="coerce",
        )

    stock_df = stock_df.dropna(
        subset=["closing_stock_t"]
    ).copy()

    if stock_df.empty:
        return {
            "status": "insufficient_inventory_data",
            "rows": 0,
        }

    # Inventory states
    stock_df["stockout_flag"] = (
        stock_df["closing_stock_t"] <= 0
    ).astype(int)

    stock_df["low_stock_flag_phase5"] = (
        (stock_df["closing_stock_t"] > 0)
        & (stock_df["closing_stock_t"] <= 5)
    ).astype(int)

    stock_df["inventory_pressure_flag"] = (
        stock_df["closing_stock_t"] <= 5
    ).astype(int)

    total_rows = int(len(stock_df))

    stockout_rows = int(
        stock_df["stockout_flag"].sum()
    )

    low_stock_rows = int(
        stock_df["low_stock_flag_phase5"].sum()
    )

    pressure_rows = int(
        stock_df["inventory_pressure_flag"].sum()
    )

    stockout_pct = (
        stockout_rows / total_rows * 100
        if total_rows
        else 0
    )

    low_stock_pct = (
        low_stock_rows / total_rows * 100
        if total_rows
        else 0
    )

    pressure_pct = (
        pressure_rows / total_rows * 100
        if total_rows
        else 0
    )

    result = {
        "status": "analyzed",
        "rows": total_rows,
        "stockout_rows": stockout_rows,
        "stockout_pct": round(
            stockout_pct,
            2,
        ),
        "low_stock_rows": low_stock_rows,
        "low_stock_pct": round(
            low_stock_pct,
            2,
        ),
        "inventory_pressure_rows": pressure_rows,
        "inventory_pressure_pct": round(
            pressure_pct,
            2,
        ),
    }

    # Compare observed sales under different inventory conditions
    if "units_sold_t" in stock_df.columns:
        sales_df = stock_df.dropna(
            subset=["units_sold_t"]
        ).copy()

        normal_inventory_sales = sales_df[
            sales_df["closing_stock_t"] > 5
        ]["units_sold_t"]

        pressured_inventory_sales = sales_df[
            sales_df["closing_stock_t"] <= 5
        ]["units_sold_t"]

        stockout_sales = sales_df[
            sales_df["closing_stock_t"] <= 0
        ]["units_sold_t"]

        result["sales_diagnostics"] = {
            "average_sales_normal_inventory": (
                round(
                    float(
                        normal_inventory_sales.mean()
                    ),
                    4,
                )
                if not normal_inventory_sales.empty
                else None
            ),
            "average_sales_inventory_pressure": (
                round(
                    float(
                        pressured_inventory_sales.mean()
                    ),
                    4,
                )
                if not pressured_inventory_sales.empty
                else None
            ),
            "average_sales_stockout": (
                round(
                    float(
                        stockout_sales.mean()
                    ),
                    4,
                )
                if not stockout_sales.empty
                else None
            ),
        }

    if pressure_pct >= 20:
        risk_level = "HIGH"
        interpretation = (
            "A substantial share of observations occur under low "
            "or zero inventory. Observed sales may materially "
            "understate underlying demand."
        )

    elif pressure_pct >= 5:
        risk_level = "MODERATE"
        interpretation = (
            "Some observations occur under inventory pressure. "
            "Observed sales should be interpreted cautiously for "
            "those periods."
        )

    else:
        risk_level = "LOW"
        interpretation = (
            "Inventory pressure affects a relatively small share "
            "of observations, although individual stockout periods "
            "may still suppress observed demand."
        )

    result["suppressed_demand_risk"] = {
        "level": risk_level,
        "interpretation": interpretation,
    }

    result["methodology_note"] = (
        "This diagnostic identifies conditions where observed sales "
        "may be inventory-constrained. It does not infer or impute "
        "unobserved latent demand."
    )

    return result


def add_inventory_demand_status(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add interpretable inventory-demand status fields
    to the Phase 5 causal dataset.
    """

    result_df = df.copy()

    if "closing_stock_t" not in result_df.columns:
        result_df["demand_observation_status"] = (
            "inventory_unknown"
        )
        return result_df

    closing_stock = pd.to_numeric(
        result_df["closing_stock_t"],
        errors="coerce",
    )

    result_df["demand_observation_status"] = (
        "inventory_available"
    )

    result_df.loc[
        closing_stock <= 5,
        "demand_observation_status",
    ] = "inventory_pressure"

    result_df.loc[
        closing_stock <= 0,
        "demand_observation_status",
    ] = "stockout"

    result_df.loc[
        closing_stock.isna(),
        "demand_observation_status",
    ] = "inventory_unknown"

    return result_df