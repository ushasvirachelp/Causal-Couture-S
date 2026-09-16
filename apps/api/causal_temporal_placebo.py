from typing import Any

import numpy as np
import pandas as pd


def run_temporal_placebo_test(df: pd.DataFrame) -> dict[str, Any]:
    """
    Temporal falsification / negative-control exposure diagnostic.

    Tests whether FUTURE next-calendar-day engagement predicts CURRENT sales.
    Future exposure cannot cause a past outcome, so this is a falsification
    diagnostic rather than a causal estimate.
    """
    required = [
        "date", "sku_id", "engagement_rate_t", "units_sold_t",
        "units_sold_lag1", "engagement_rate_lag1",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns for temporal placebo test: {missing}")

    placebo_df = df.copy()
    placebo_df["date"] = pd.to_datetime(placebo_df["date"], errors="coerce")
    placebo_df = placebo_df.sort_values(["sku_id", "date"]).reset_index(drop=True)

    placebo_df["future_engagement_rate"] = (
        placebo_df.groupby("sku_id")["engagement_rate_t"].shift(-1)
    )
    placebo_df["future_engagement_date"] = (
        placebo_df.groupby("sku_id")["date"].shift(-1)
    )
    placebo_df["days_to_future_engagement"] = (
        placebo_df["future_engagement_date"] - placebo_df["date"]
    ).dt.days

    placebo_df.loc[
        placebo_df["days_to_future_engagement"] != 1,
        "future_engagement_rate",
    ] = np.nan

    if "inventory_constrained_flag" in placebo_df.columns:
        placebo_df = placebo_df[
            placebo_df["inventory_constrained_flag"] == 0
        ].copy()

    numeric = [
        "units_sold_t", "future_engagement_rate",
        "units_sold_lag1", "engagement_rate_lag1",
    ]
    if "closing_stock_t" in placebo_df.columns:
        numeric.append("closing_stock_t")

    for c in numeric:
        placebo_df[c] = pd.to_numeric(placebo_df[c], errors="coerce")

    model_df = placebo_df.dropna(
        subset=[
            "date", "sku_id", "units_sold_t", "future_engagement_rate",
            "units_sold_lag1", "engagement_rate_lag1",
        ]
    ).copy()

    if len(model_df) < 10:
        return {
            "status": "insufficient_data",
            "rows_used": int(len(model_df)),
            "placebo_exposure": "future_engagement_rate_t_plus_1",
            "placebo_outcome": "units_sold_t",
            "reason": (
                "At least 10 eligible next-calendar-day observations are "
                "required for the temporal placebo diagnostic."
            ),
        }

    adjustments = ["units_sold_lag1", "engagement_rate_lag1"]
    if (
        "closing_stock_t" in model_df.columns
        and model_df["closing_stock_t"].notna().all()
    ):
        adjustments.append("closing_stock_t")

    sku_dummies = pd.get_dummies(
        model_df["sku_id"].astype(str),
        prefix="sku", drop_first=True, dtype=float,
    )

    model_df["day_of_week"] = model_df["date"].dt.dayofweek
    dow_dummies = pd.get_dummies(
        model_df["day_of_week"],
        prefix="dow", drop_first=True, dtype=float,
    )

    base_x = model_df[
        ["future_engagement_rate", *adjustments]
    ].astype(float)

    x_df = pd.concat(
        [
            base_x.reset_index(drop=True),
            sku_dummies.reset_index(drop=True),
            dow_dummies.reset_index(drop=True),
        ],
        axis=1,
    )

    y = model_df["units_sold_t"].astype(float).to_numpy()
    x = x_df.to_numpy(dtype=float)
    x = np.column_stack([np.ones(len(x)), x])

    beta, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
    placebo_effect = float(beta[1])

    fitted = x @ beta
    ss_res = float(np.sum((y - fitted) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else None

    return {
        "status": "estimated",
        "diagnostic_type": "temporal_falsification_negative_control",
        "rows_used": int(len(model_df)),
        "unique_skus": int(model_df["sku_id"].nunique()),
        "placebo_exposure": "future_engagement_rate_t_plus_1",
        "placebo_outcome": "units_sold_t",
        "temporal_rule": (
            "Only engagement observed on the next calendar day is used "
            "as the future placebo exposure."
        ),
        "adjustment_strategy": [
            "prior sales",
            "prior engagement",
            *(
                ["current inventory availability"]
                if "closing_stock_t" in adjustments else []
            ),
            "SKU fixed effects",
            "day-of-week effects",
        ],
        "temporal_placebo_effect": round(placebo_effect, 6),
        "r_squared": (
            round(float(r_squared), 6) if r_squared is not None else None
        ),
        "design_rank": int(rank),
        "interpretation": (
            "This intentionally tests a temporally impossible direction: "
            "future engagement predicting current sales. A coefficient near "
            "zero is more reassuring than a large coefficient, while a large "
            "coefficient can flag residual temporal structure, confounding, "
            "or model misspecification. This diagnostic does not prove or "
            "disprove causal identification by itself."
        ),
        "causal_boundary": (
            "Future engagement cannot cause past sales. The test is used "
            "as a falsification diagnostic, not as a causal estimate."
        ),
    }
