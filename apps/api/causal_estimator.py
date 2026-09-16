import numpy as np
import pandas as pd


def estimate_engagement_effect(df: pd.DataFrame) -> dict:
    """
    Estimate the association between social engagement at time t
    and units sold on the next calendar day.

    The model adjusts for:
    - prior sales
    - prior engagement
    - current inventory when available
    - SKU fixed effects
    - day-of-week effects

    This is an observational estimate and depends on the causal
    assumptions defined in the Phase 5 DAG.
    """

    required_columns = [
        "date",
        "sku_id",
        "engagement_rate_t",
        "units_sold_next_day",
        "units_sold_lag1",
        "engagement_rate_lag1",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required causal columns: {missing}"
        )

    model_df = df.copy()

    # Keep only temporally valid causal rows
    if "causal_row_valid" in model_df.columns:
        model_df = model_df[
            model_df["causal_row_valid"] == 1
        ].copy()

    # Remove observations where sales may be completely
    # suppressed because inventory reached zero
    if "inventory_constrained_flag" in model_df.columns:
        model_df = model_df[
            model_df["inventory_constrained_flag"] == 0
        ].copy()

    model_df["date"] = pd.to_datetime(
        model_df["date"],
        errors="coerce",
    )

    # Time control
    model_df["day_of_week"] = (
        model_df["date"].dt.dayofweek
    )

    adjustment_columns = [
        "units_sold_lag1",
        "engagement_rate_lag1",
    ]

    if "closing_stock_t" in model_df.columns:
        adjustment_columns.append(
            "closing_stock_t"
        )

    required_model_columns = [
        "units_sold_next_day",
        "engagement_rate_t",
        "sku_id",
        "day_of_week",
        *adjustment_columns,
    ]

    model_df = model_df[
        required_model_columns
    ].dropna()

    if len(model_df) < 10:
        return {
            "status": "insufficient_data",
            "rows_used": int(len(model_df)),
            "minimum_rows_required": 10,
            "message": (
                "Not enough valid observations are available "
                "for the causal-effect estimate."
            ),
        }

    y = (
        model_df["units_sold_next_day"]
        .astype(float)
    )

    # Base numeric predictors
    X = model_df[
        [
            "engagement_rate_t",
            *adjustment_columns,
        ]
    ].astype(float)

    # SKU fixed effects
    sku_effects = pd.get_dummies(
        model_df["sku_id"].astype(str),
        prefix="sku",
        drop_first=True,
        dtype=float,
    )

    # Day-of-week fixed effects
    time_effects = pd.get_dummies(
        model_df["day_of_week"].astype(str),
        prefix="dow",
        drop_first=True,
        dtype=float,
    )

    X = pd.concat(
        [
            X.reset_index(drop=True),
            sku_effects.reset_index(drop=True),
            time_effects.reset_index(drop=True),
        ],
        axis=1,
    )

    # Add intercept
    X.insert(
        0,
        "intercept",
        1.0,
    )

    X_matrix = X.to_numpy(dtype=float)
    y_array = y.to_numpy(dtype=float)

    beta, _, _, _ = np.linalg.lstsq(
        X_matrix,
        y_array,
        rcond=None,
    )

    coefficients = {
        column: float(value)
        for column, value in zip(
            X.columns,
            beta,
        )
    }

    engagement_effect = coefficients[
        "engagement_rate_t"
    ]

    predictions = X_matrix @ beta
    residuals = y_array - predictions

    ss_res = float(
        np.sum(residuals ** 2)
    )

    ss_tot = float(
        np.sum(
            (y_array - np.mean(y_array)) ** 2
        )
    )

    r_squared = (
        1 - (ss_res / ss_tot)
        if ss_tot > 0
        else 0.0
    )

    return {
        "status": "estimated",
        "analysis_type": (
            "adjusted_linear_effect_estimate"
        ),
        "rows_used": int(len(model_df)),
        "treatment": "engagement_rate_t",
        "outcome": "units_sold_next_day",
        "adjustment_variables": (
            adjustment_columns
        ),
        "fixed_effects": [
            "sku_id",
            "day_of_week",
        ],
        "estimated_engagement_effect": round(
            engagement_effect,
            6,
        ),
        "r_squared": round(
            r_squared,
            4,
        ),
        "interpretation": (
            "The engagement coefficient represents the estimated "
            "difference in next-day units sold associated with a "
            "one-unit increase in engagement_rate, conditional on "
            "prior demand, prior engagement, available inventory, "
            "SKU differences, and day-of-week effects."
        ),
        "causal_warning": (
            "This estimate is based on observational data. "
            "A causal interpretation requires the DAG assumptions, "
            "adequate confounder measurement, treatment overlap, "
            "correct temporal ordering, and robustness checks to "
            "remain credible."
        ),
    }