import pandas as pd


def clamp_score(value: float) -> float:
    """Keep an analytical score between 0 and 100."""
    return round(max(0, min(100, float(value))), 2)


def calculate_demand_pressure(df: pd.DataFrame) -> float:
    """
    Estimate demand pressure from the available sales features.
    This is a heuristic signal, not a forecast or causal estimate.
    """
    if "units_sold" not in df.columns:
        return 0.0

    units = pd.to_numeric(df["units_sold"], errors="coerce").fillna(0)

    if units.empty or units.max() == 0:
        return 0.0

    average_units = units.mean()
    peak_units = units.max()

    score = (average_units / peak_units) * 100

    if "sales_spike_flag" in df.columns:
        spike_rate = (
            pd.to_numeric(df["sales_spike_flag"], errors="coerce")
            .fillna(0)
            .mean()
        )
        score = (score * 0.8) + (spike_rate * 100 * 0.2)

    return clamp_score(score)


def calculate_stock_risk(df: pd.DataFrame) -> float:
    """
    Estimate inventory pressure from closing stock and low-stock signals.
    """
    if "closing_stock" not in df.columns:
        return 0.0

    stock = pd.to_numeric(
        df["closing_stock"], errors="coerce"
    ).fillna(0)

    if stock.empty:
        return 0.0

    low_stock_component = 0.0

    if "low_stock_flag" in df.columns:
        low_stock_component = (
            pd.to_numeric(df["low_stock_flag"], errors="coerce")
            .fillna(0)
            .mean()
            * 100
        )

    average_stock = stock.mean()
    maximum_stock = stock.max()

    availability_risk = 0.0

    if maximum_stock > 0:
        availability_risk = (
            1 - (average_stock / maximum_stock)
        ) * 100

    score = (
        low_stock_component * 0.7
        + availability_risk * 0.3
    )

    return clamp_score(score)


def calculate_engagement_momentum(df: pd.DataFrame) -> float:
    """
    Estimate engagement strength from engagement-rate features.
    """
    if "engagement_rate" not in df.columns:
        return 0.0

    engagement = pd.to_numeric(
        df["engagement_rate"], errors="coerce"
    ).fillna(0)

    if engagement.empty:
        return 0.0

    score = engagement.mean() * 100

    if "social_spike_flag" in df.columns:
        spike_rate = (
            pd.to_numeric(df["social_spike_flag"], errors="coerce")
            .fillna(0)
            .mean()
        )

        score = (score * 0.85) + (spike_rate * 100 * 0.15)

    return clamp_score(score)


def calculate_conversion_strength(df: pd.DataFrame) -> float:
    """
    Estimate conversion strength from view-to-cart behavior.
    """
    if "view_to_cart_rate" not in df.columns:
        return 0.0

    conversion = pd.to_numeric(
        df["view_to_cart_rate"], errors="coerce"
    ).fillna(0)

    if conversion.empty:
        return 0.0

    return clamp_score(conversion.mean() * 100)


def calculate_overall_signal(
    demand: float,
    stock: float,
    engagement: float,
    conversion: float,
) -> float:
    """
    Combine the four heuristic business signals.

    Stock risk is inverted because higher stock risk is negative,
    while the other three signals are positive.
    """
    stock_health = 100 - stock

    score = (
        demand * 0.35
        + stock_health * 0.25
        + engagement * 0.20
        + conversion * 0.20
    )

    return clamp_score(score)


def generate_recommendation(
    demand: float,
    stock: float,
    engagement: float,
    conversion: float,
    overall: float,
) -> dict:
    """
    Generate a structured rule-based recommendation.
    """

    if demand >= 65 and stock >= 55:
        return {
            "action": "REORDER",
            "priority": "HIGH",
            "confidence": "MEDIUM",
            "reason": (
                "Demand pressure is strong while inventory risk is elevated."
            ),
        }

    if demand >= 55 and stock >= 35:
        return {
            "action": "MONITOR",
            "priority": "MEDIUM",
            "confidence": "MEDIUM",
            "reason": (
                "Demand is strengthening and inventory pressure should be monitored."
            ),
        }

    if engagement >= 65 and conversion < 35:
        return {
            "action": "MONITOR",
            "priority": "MEDIUM",
            "confidence": "LOW",
            "reason": (
                "Engagement is strong but conversion remains weak."
            ),
        }

    if overall < 35 and demand < 40:
        return {
            "action": "DEPRIORITIZE",
            "priority": "LOW",
            "confidence": "MEDIUM",
            "reason": (
                "Current demand signals are weak and do not indicate immediate inventory pressure."
            ),
        }

    return {
        "action": "HOLD",
        "priority": "LOW",
        "confidence": "MEDIUM",
        "reason": (
            "Current demand and inventory signals do not require an immediate change."
        ),
    }


def build_scorecard(df: pd.DataFrame) -> dict:
    """
    Build the complete reusable Causal Couture scorecard.
    """

    demand = calculate_demand_pressure(df)
    stock = calculate_stock_risk(df)
    engagement = calculate_engagement_momentum(df)
    conversion = calculate_conversion_strength(df)

    overall = calculate_overall_signal(
        demand,
        stock,
        engagement,
        conversion,
    )

    recommendation = generate_recommendation(
        demand,
        stock,
        engagement,
        conversion,
        overall,
    )

    return {
        "analysis_type": "heuristic_business_signal_scorecard",
        "demand_pressure_score": demand,
        "stock_risk_score": stock,
        "engagement_momentum_score": engagement,
        "conversion_strength_score": conversion,
        "overall_signal_score": overall,
        "recommendation": recommendation,
        "methodology_note": (
            "Scores are heuristic decision-support signals. "
            "They are not causal estimates or forecasts."
        ),
    }