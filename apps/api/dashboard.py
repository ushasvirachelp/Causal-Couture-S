from typing import Any

import pandas as pd

from analytics import build_scorecard
from trends import build_trend_summary
from alerts import generate_alerts


def build_dataset_summary(df: pd.DataFrame) -> dict[str, Any]:
    """
    Return basic information about the unified dataset.
    """

    summary = {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "unique_skus": 0,
        "date_start": None,
        "date_end": None,
    }

    if "sku_id" in df.columns:
        summary["unique_skus"] = int(df["sku_id"].nunique())

    if "date" in df.columns:
        dates = pd.to_datetime(df["date"], errors="coerce").dropna()

        if not dates.empty:
            summary["date_start"] = str(dates.min().date())
            summary["date_end"] = str(dates.max().date())

    return summary


def build_data_source_status(df: pd.DataFrame) -> dict[str, Any]:
    """
    Identify which business-data sources are represented
    in the unified dataset.
    """

    columns = set(df.columns)

    return {
        "sales": {
            "available": "units_sold" in columns,
        },
        "inventory": {
            "available": "closing_stock" in columns,
        },
        "social": {
            "available": (
                "engagement" in columns
                or "engagement_rate" in columns
            ),
        },
        "web": {
            "available": (
                "product_views" in columns
                or "view_to_cart_rate" in columns
            ),
        },
    }


def build_dashboard(df: pd.DataFrame) -> dict[str, Any]:
    """
    Build the primary executive dashboard payload.

    Combines current business signals, descriptive trends,
    recommendations, alerts, and dataset health information.
    """

    scorecard = build_scorecard(df)

    trend_summary = build_trend_summary(df)

    alerts = generate_alerts(
        scorecard,
        trend_summary["trends"],
    )

    recommendation = scorecard["recommendation"]

    dataset_summary = build_dataset_summary(df)

    source_status = build_data_source_status(df)

    return {
        "dashboard_version": "1.0",
        "analysis_type": "executive_retail_intelligence_dashboard",

        "kpis": {
            "demand_pressure": {
                "score": scorecard["demand_pressure_score"],
                "trend": trend_summary["trends"]["demand"],
            },

            "stock_risk": {
                "score": scorecard["stock_risk_score"],
                "trend": trend_summary["trends"]["inventory"],
            },

            "engagement_momentum": {
                "score": scorecard["engagement_momentum_score"],
                "trend": trend_summary["trends"]["engagement"],
            },

            "conversion_strength": {
                "score": scorecard["conversion_strength_score"],
                "trend": trend_summary["trends"]["conversion"],
            },

            "overall_signal": {
                "score": scorecard["overall_signal_score"],
            },
        },

        "recommendation": recommendation,

        "alerts": alerts,

        "dataset": dataset_summary,

        "data_sources": source_status,

        "methodology": {
            "scorecard": (
                "Heuristic business-signal scoring."
            ),
            "trends": (
                "Descriptive previous-versus-recent period comparison."
            ),
            "alerts": (
                "Rule-based operational alerts."
            ),
            "causal_status": (
                "No causal effect estimation is performed in this dashboard."
            ),
        },
    }