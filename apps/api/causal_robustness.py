import numpy as np
import pandas as pd


def _fit_linear_model(
    df: pd.DataFrame,
    adjustment_columns: list[str],
    include_sku_effects: bool = True,
    include_time_effects: bool = True,
) -> dict:
    """
    Fit one linear specification for robustness comparison.
    """

    model_df = df.copy()

    if "causal_row_valid" in model_df.columns:
        model_df = model_df[
            model_df["causal_row_valid"] == 1
        ].copy()

    if "inventory_constrained_flag" in model_df.columns:
        model_df = model_df[
            model_df["inventory_constrained_flag"] == 0
        ].copy()

    required = [
        "date",
        "sku_id",
        "engagement_rate_t",
        "units_sold_next_day",
        *adjustment_columns,
    ]

    missing = [
        column
        for column in required
        if column not in model_df.columns
    ]

    if missing:
        return {
            "status": "missing_columns",
            "missing_columns": missing,
        }

    model_df["date"] = pd.to_datetime(
        model_df["date"],
        errors="coerce",
    )

    model_df["day_of_week"] = (
        model_df["date"].dt.dayofweek
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
        }

    y = (
        model_df["units_sold_next_day"]
        .astype(float)
    )

    X = model_df[
        [
            "engagement_rate_t",
            *adjustment_columns,
        ]
    ].astype(float)

    if include_sku_effects:
        sku_effects = pd.get_dummies(
            model_df["sku_id"].astype(str),
            prefix="sku",
            drop_first=True,
            dtype=float,
        )

        X = pd.concat(
            [
                X.reset_index(drop=True),
                sku_effects.reset_index(drop=True),
            ],
            axis=1,
        )

    if include_time_effects:
        time_effects = pd.get_dummies(
            model_df["day_of_week"].astype(str),
            prefix="dow",
            drop_first=True,
            dtype=float,
        )

        X = pd.concat(
            [
                X.reset_index(drop=True),
                time_effects.reset_index(drop=True),
            ],
            axis=1,
        )

    X.insert(
        0,
        "intercept",
        1.0,
    )

    X_matrix = X.to_numpy(
        dtype=float
    )

    y_array = y.to_numpy(
        dtype=float
    )

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

    effect = coefficients.get(
        "engagement_rate_t"
    )

    predictions = (
        X_matrix @ beta
    )

    residuals = (
        y_array - predictions
    )

    ss_res = float(
        np.sum(
            residuals ** 2
        )
    )

    ss_tot = float(
        np.sum(
            (y_array - np.mean(y_array)) ** 2
        )
    )

    r_squared = (
        1 - ss_res / ss_tot
        if ss_tot > 0
        else 0.0
    )

    return {
        "status": "estimated",
        "rows_used": int(len(model_df)),
        "estimated_engagement_effect": round(
            float(effect),
            6,
        ),
        "r_squared": round(
            r_squared,
            4,
        ),
        "adjustment_variables": adjustment_columns,
        "sku_fixed_effects": include_sku_effects,
        "time_fixed_effects": include_time_effects,
    }


def run_robustness_checks(
    df: pd.DataFrame,
) -> dict:
    """
    Compare the engagement estimate across several reasonable
    observational model specifications.

    Stable direction and magnitude across specifications provide
    more reassurance than an estimate that changes dramatically.
    """

    specifications = {}

    # ---------------------------------------------------------
    # MODEL 1 — Minimal temporal adjustment
    # ---------------------------------------------------------

    specifications["minimal_adjustment"] = (
        _fit_linear_model(
            df=df,
            adjustment_columns=[
                "units_sold_lag1",
                "engagement_rate_lag1",
            ],
            include_sku_effects=False,
            include_time_effects=False,
        )
    )

    # ---------------------------------------------------------
    # MODEL 2 — Add inventory
    # ---------------------------------------------------------

    inventory_adjustments = [
        "units_sold_lag1",
        "engagement_rate_lag1",
    ]

    if "closing_stock_t" in df.columns:
        inventory_adjustments.append(
            "closing_stock_t"
        )

    specifications[
        "inventory_adjusted"
    ] = _fit_linear_model(
        df=df,
        adjustment_columns=inventory_adjustments,
        include_sku_effects=False,
        include_time_effects=False,
    )

    # ---------------------------------------------------------
    # MODEL 3 — Add SKU fixed effects
    # ---------------------------------------------------------

    specifications[
        "sku_adjusted"
    ] = _fit_linear_model(
        df=df,
        adjustment_columns=inventory_adjustments,
        include_sku_effects=True,
        include_time_effects=False,
    )

    # ---------------------------------------------------------
    # MODEL 4 — Full preferred specification
    # ---------------------------------------------------------

    specifications[
        "preferred_model"
    ] = _fit_linear_model(
        df=df,
        adjustment_columns=inventory_adjustments,
        include_sku_effects=True,
        include_time_effects=True,
    )

    # ---------------------------------------------------------
    # COLLECT EFFECTS
    # ---------------------------------------------------------

    valid_effects = []

    for name, result in specifications.items():
        if (
            result.get("status") == "estimated"
            and result.get(
                "estimated_engagement_effect"
            )
            is not None
        ):
            valid_effects.append(
                {
                    "model": name,
                    "effect": float(
                        result[
                            "estimated_engagement_effect"
                        ]
                    ),
                }
            )

    if len(valid_effects) < 2:
        return {
            "status": "insufficient_models",
            "specifications": specifications,
            "message": (
                "Not enough model specifications could be "
                "estimated for robustness comparison."
            ),
        }

    effects = [
        item["effect"]
        for item in valid_effects
    ]

    positive = sum(
        effect > 0
        for effect in effects
    )

    negative = sum(
        effect < 0
        for effect in effects
    )

    zero = sum(
        effect == 0
        for effect in effects
    )

    if positive == len(effects):
        direction_consistency = "positive"

    elif negative == len(effects):
        direction_consistency = "negative"

    elif zero == len(effects):
        direction_consistency = "neutral"

    else:
        direction_consistency = "mixed"

    effect_min = min(effects)
    effect_max = max(effects)

    effect_range = (
        effect_max - effect_min
    )

    preferred = specifications.get(
        "preferred_model",
        {},
    ).get(
        "estimated_engagement_effect"
    )

    # ---------------------------------------------------------
    # BUSINESS-SCALE INTERPRETATION
    # ---------------------------------------------------------

    effect_per_10pct = None

    if preferred is not None:
        # engagement_rate generally ranges from 0 to 1.
        # A +0.10 change corresponds to +10 percentage points.
        effect_per_10pct = (
            float(preferred) * 0.10
        )

    # ---------------------------------------------------------
    # ROBUSTNESS LABEL
    # ---------------------------------------------------------

    if direction_consistency in {
        "positive",
        "negative",
    }:
        robustness_status = (
            "DIRECTIONALLY_STABLE"
        )

        interpretation = (
            "The estimated engagement effect keeps the same "
            "direction across the tested model specifications."
        )

    else:
        robustness_status = (
            "SPECIFICATION_SENSITIVE"
        )

        interpretation = (
            "The estimated engagement effect changes direction "
            "across model specifications and should be interpreted "
            "with additional caution."
        )

    return {
        "status": "evaluated",
        "models_estimated": int(
            len(valid_effects)
        ),
        "direction_consistency": (
            direction_consistency
        ),
        "effect_range": {
            "minimum": round(
                effect_min,
                6,
            ),
            "maximum": round(
                effect_max,
                6,
            ),
            "spread": round(
                effect_range,
                6,
            ),
        },
        "preferred_effect": (
            round(
                float(preferred),
                6,
            )
            if preferred is not None
            else None
        ),
        "preferred_effect_per_10_percentage_point_engagement_increase": (
            round(
                effect_per_10pct,
                6,
            )
            if effect_per_10pct is not None
            else None
        ),
        "robustness_status": robustness_status,
        "specifications": specifications,
        "interpretation": interpretation,
        "methodology_note": (
            "Model-specification stability is a robustness diagnostic. "
            "It does not establish that all confounding has been removed."
        ),
    }