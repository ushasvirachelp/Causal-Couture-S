from typing import Any
import pandas as pd


def safe_pct_change(previous: float, recent: float) -> float:
    """
    Calculate percent change safely.
    """
    if previous == 0:
        if recent == 0:
            return 0.0
        return 100.0

    return round(((recent - previous) / abs(previous)) * 100, 2)


def trend_label(change_pct: float) -> str:
    """
    Convert percent change into a simple trend label.
    """
    if change_pct >= 10:
        return "increasing"

    if change_pct <= -10:
        return "declining"

    return "stable"


def trend_direction(change_pct: float) -> str:
    if change_pct > 2:
        return "up"

    if change_pct < -2:
        return "down"

    return "flat"


def split_periods(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split the dataset into two chronological halves.

    The first half is the comparison period.
    The second half is the recent period.
    """
    if "date" not in df.columns:
        raise ValueError("Trend analysis requires a date column.")

    working = df.copy()

    working["date"] = pd.to_datetime(
        working["date"],
        errors="coerce",
    )

    working = working.dropna(subset=["date"])

    if working.empty:
        raise ValueError(
            "No valid dated records are available for trend analysis."
        )

    working = working.sort_values("date")

    midpoint = len(working) // 2

    if midpoint == 0:
        return working.copy(), working.copy()

    previous = working.iloc[:midpoint].copy()
    recent = working.iloc[midpoint:].copy()

    return previous, recent


def mean_numeric(
    df: pd.DataFrame,
    column: str,
) -> float:
    if column not in df.columns:
        return 0.0

    values = pd.to_numeric(
        df[column],
        errors="coerce",
    ).dropna()

    if values.empty:
        return 0.0

    return float(values.mean())


def build_single_trend(
    previous_value: float,
    recent_value: float,
) -> dict[str, Any]:
    change = safe_pct_change(
        previous_value,
        recent_value,
    )

    return {
        "previous_value": round(previous_value, 2),
        "recent_value": round(recent_value, 2),
        "change_pct": change,
        "direction": trend_direction(change),
        "label": trend_label(change),
    }


def build_trend_summary(
    df: pd.DataFrame,
) -> dict[str, Any]:
    """
    Build recent-vs-previous period trend indicators.

    This is descriptive trend analysis.
    It does not represent forecasting or causal estimation.
    """

    previous, recent = split_periods(df)

    previous_demand = mean_numeric(
        previous,
        "units_sold",
    )

    recent_demand = mean_numeric(
        recent,
        "units_sold",
    )

    previous_inventory = mean_numeric(
        previous,
        "closing_stock",
    )

    recent_inventory = mean_numeric(
        recent,
        "closing_stock",
    )

    previous_engagement = mean_numeric(
        previous,
        "engagement_rate",
    )

    recent_engagement = mean_numeric(
        recent,
        "engagement_rate",
    )

    previous_conversion = mean_numeric(
        previous,
        "view_to_cart_rate",
    )

    recent_conversion = mean_numeric(
        recent,
        "view_to_cart_rate",
    )

    trends = {
        "demand": build_single_trend(
            previous_demand,
            recent_demand,
        ),
        "inventory": build_single_trend(
            previous_inventory,
            recent_inventory,
        ),
        "engagement": build_single_trend(
            previous_engagement,
            recent_engagement,
        ),
        "conversion": build_single_trend(
            previous_conversion,
            recent_conversion,
        ),
    }

    return {
        "analysis_type": "descriptive_period_trend_analysis",
        "comparison_method": (
            "The dated dataset is split chronologically into "
            "previous and recent comparison periods."
        ),
        "previous_period_rows": int(len(previous)),
        "recent_period_rows": int(len(recent)),
        "trends": trends,
        "methodology_note": (
            "Trend indicators describe changes within the available "
            "data. They are not forecasts or causal estimates."
        ),
    }