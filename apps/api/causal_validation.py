import numpy as np
import pandas as pd


def bootstrap_engagement_effect(
    df: pd.DataFrame,
    estimator_function,
    n_bootstrap: int = 300,
    random_state: int = 42,
) -> dict:
    """
    Bootstrap the engagement effect estimate to provide a simple
    uncertainty interval around the first Phase 5 estimator.
    """

    rng = np.random.default_rng(random_state)

    if df.empty:
        return {
            "status": "insufficient_data",
            "bootstrap_samples": 0,
        }

    effects = []

    for _ in range(n_bootstrap):
        sample_indices = rng.integers(
            0,
            len(df),
            size=len(df),
        )

        sample_df = df.iloc[sample_indices].copy()

        result = estimator_function(sample_df)

        if (
            result.get("status") == "estimated"
            and result.get("estimated_engagement_effect") is not None
        ):
            effects.append(
                float(result["estimated_engagement_effect"])
            )

    if len(effects) < 30:
        return {
            "status": "insufficient_bootstrap_estimates",
            "successful_samples": int(len(effects)),
            "requested_samples": int(n_bootstrap),
        }

    effects = np.array(effects)

    return {
        "status": "estimated",
        "bootstrap_samples": int(len(effects)),
        "mean_effect": round(float(np.mean(effects)), 6),
        "median_effect": round(float(np.median(effects)), 6),
        "confidence_interval_95": {
            "lower": round(
                float(np.percentile(effects, 2.5)),
                6,
            ),
            "upper": round(
                float(np.percentile(effects, 97.5)),
                6,
            ),
        },
        "std_error_bootstrap": round(
            float(np.std(effects, ddof=1)),
            6,
        ),
    }


def run_placebo_test(
    df: pd.DataFrame,
    random_state: int = 42,
) -> dict:
    """
    Simple placebo diagnostic.

    The treatment is randomly shuffled across rows. If the original
    relationship is meaningful, the shuffled treatment should generally
    lose much of its predictive relationship with the outcome.
    """

    required = [
        "engagement_rate_t",
        "units_sold_next_day",
        "units_sold_lag1",
        "engagement_rate_lag1",
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing columns for placebo test: {missing}"
        )

    placebo_df = df.copy()

    if "causal_row_valid" in placebo_df.columns:
        placebo_df = placebo_df[
            placebo_df["causal_row_valid"] == 1
        ].copy()

    if "inventory_constrained_flag" in placebo_df.columns:
        placebo_df = placebo_df[
            placebo_df["inventory_constrained_flag"] == 0
        ].copy()

    adjustment_columns = [
        "units_sold_lag1",
        "engagement_rate_lag1",
    ]

    if "closing_stock_t" in placebo_df.columns:
        adjustment_columns.append("closing_stock_t")

    model_columns = [
        "units_sold_next_day",
        "engagement_rate_t",
        *adjustment_columns,
    ]

    placebo_df = placebo_df[model_columns].dropna()

    if len(placebo_df) < 10:
        return {
            "status": "insufficient_data",
            "rows_used": int(len(placebo_df)),
        }

    rng = np.random.default_rng(random_state)

    placebo_df["placebo_engagement"] = rng.permutation(
        placebo_df["engagement_rate_t"].to_numpy()
    )

    y = (
        placebo_df["units_sold_next_day"]
        .astype(float)
        .to_numpy()
    )

    predictor_columns = [
        "placebo_engagement",
        *adjustment_columns,
    ]

    X = (
        placebo_df[predictor_columns]
        .astype(float)
        .to_numpy()
    )

    X = np.column_stack(
        [
            np.ones(len(X)),
            X,
        ]
    )

    beta, _, _, _ = np.linalg.lstsq(
        X,
        y,
        rcond=None,
    )

    placebo_effect = float(beta[1])

    return {
        "status": "estimated",
        "rows_used": int(len(placebo_df)),
        "placebo_treatment": "shuffled_engagement_rate_t",
        "placebo_effect": round(
            placebo_effect,
            6,
        ),
        "interpretation": (
            "The placebo treatment is randomly shuffled engagement. "
            "A placebo effect near zero provides more reassurance than "
            "a large placebo effect, but this diagnostic alone does not "
            "validate causal identification."
        ),
    }