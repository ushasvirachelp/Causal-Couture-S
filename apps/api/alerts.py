from typing import Any


def build_alert(
    category: str,
    severity: str,
    title: str,
    message: str,
) -> dict[str, Any]:
    return {
        "category": category,
        "severity": severity,
        "title": title,
        "message": message,
    }


def generate_alerts(
    scorecard: dict[str, Any],
    trends: dict[str, Any],
) -> list[dict[str, Any]]:
    alerts = []

    demand = scorecard.get("demand_pressure_score", 0)
    stock = scorecard.get("stock_risk_score", 0)
    engagement = scorecard.get("engagement_momentum_score", 0)
    conversion = scorecard.get("conversion_strength_score", 0)

    demand_trend = trends.get("demand", {})
    inventory_trend = trends.get("inventory", {})
    engagement_trend = trends.get("engagement", {})
    conversion_trend = trends.get("conversion", {})

    if (
        demand >= 60
        and inventory_trend.get("direction") == "down"
    ):
        alerts.append(
            build_alert(
                category="inventory",
                severity="high",
                title="High Demand + Falling Inventory",
                message=(
                    "Demand pressure is elevated while recent "
                    "inventory levels are declining."
                ),
            )
        )

    if stock >= 65:
        alerts.append(
            build_alert(
                category="inventory",
                severity="high",
                title="High Stock Risk",
                message=(
                    "Current inventory conditions indicate elevated "
                    "stock pressure."
                ),
            )
        )

    if (
        engagement >= 65
        and conversion < 35
    ):
        alerts.append(
            build_alert(
                category="conversion",
                severity="medium",
                title="High Engagement + Weak Conversion",
                message=(
                    "Audience engagement is strong, but conversion "
                    "strength remains weak."
                ),
            )
        )

    if conversion_trend.get("direction") == "down":
        alerts.append(
            build_alert(
                category="conversion",
                severity="medium",
                title="Conversion Decline",
                message=(
                    "Recent conversion performance is lower than "
                    "the previous comparison period."
                ),
            )
        )

    if demand_trend.get("change_pct", 0) >= 20:
        alerts.append(
            build_alert(
                category="demand",
                severity="medium",
                title="Demand Acceleration",
                message=(
                    "Recent demand increased significantly compared "
                    "with the previous period."
                ),
            )
        )

    if engagement_trend.get("change_pct", 0) >= 25:
        alerts.append(
            build_alert(
                category="engagement",
                severity="low",
                title="Engagement Momentum",
                message=(
                    "Recent engagement increased substantially "
                    "relative to the previous period."
                ),
            )
        )

    if not alerts:
        alerts.append(
            build_alert(
                category="general",
                severity="low",
                title="No Major Alerts",
                message=(
                    "Current business signals do not indicate "
                    "an immediate issue."
                ),
            )
        )

    return alerts