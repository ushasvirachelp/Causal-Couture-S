from typing import Any

import pandas as pd

from analytics import (
    build_scorecard,
    calculate_overall_signal,
    generate_recommendation,
    clamp_score,
)


MIN_CHANGE = -100.0
MAX_CHANGE = 300.0


def validate_change(value: float, field_name: str) -> None:
    """
    Validate scenario percentage changes.

    The first scenario-engine version accepts changes between
    -100% and +300%.
    """
    if value < MIN_CHANGE or value > MAX_CHANGE:
        raise ValueError(
            f"{field_name} must be between "
            f"{MIN_CHANGE}% and {MAX_CHANGE}%."
        )


def apply_positive_signal_change(
    baseline_score: float,
    percent_change: float,
) -> float:
    """
    Apply a percentage change to a positive business signal.

    Used for demand, engagement, and conversion.
    """
    multiplier = 1 + (percent_change / 100)
    return clamp_score(baseline_score * multiplier)


def apply_inventory_change(
    baseline_stock_risk: float,
    inventory_change_pct: float,
) -> float:
    """
    Adjust stock risk based on an inventory scenario.

    Falling inventory increases stock risk.
    Increasing inventory reduces stock risk.

    Example:
    inventory_change_pct = -20
    -> stock risk rises.
    """

    # Convert stock risk to stock health.
    stock_health = 100 - baseline_stock_risk

    # Apply the user's inventory assumption.
    adjusted_stock_health = stock_health * (
        1 + inventory_change_pct / 100
    )

    adjusted_stock_health = clamp_score(adjusted_stock_health)

    # Convert health back into risk.
    scenario_stock_risk = 100 - adjusted_stock_health

    return clamp_score(scenario_stock_risk)


def compare_metric(
    baseline: float,
    scenario: float,
) -> dict[str, Any]:
    """
    Compare a baseline metric with its scenario result.
    """

    difference = round(scenario - baseline, 2)

    if difference > 0:
        direction = "increase"
    elif difference < 0:
        direction = "decrease"
    else:
        direction = "unchanged"

    return {
        "baseline": baseline,
        "scenario": scenario,
        "difference": difference,
        "direction": direction,
    }


def determine_scenario_confidence(
    demand_change_pct: float,
    inventory_change_pct: float,
    engagement_change_pct: float,
    conversion_change_pct: float,
) -> str:
    """
    Assign a simple confidence label based on the size of the
    user's assumptions.

    Larger hypothetical changes receive lower confidence because
    they move farther away from the observed baseline.
    """

    changes = [
        abs(demand_change_pct),
        abs(inventory_change_pct),
        abs(engagement_change_pct),
        abs(conversion_change_pct),
    ]

    largest_change = max(changes)

    if largest_change <= 15:
        return "MEDIUM"

    if largest_change <= 40:
        return "LOW"

    return "VERY LOW"


def build_scenario_explanation(
    baseline: dict[str, Any],
    scenario: dict[str, Any],
    recommendation: dict[str, Any],
    changes: dict[str, float],
) -> str:
    """
    Produce a concise business-facing explanation.
    """

    parts = []

    if changes["demand_change_pct"] > 0:
        parts.append(
            f"Demand was simulated {changes['demand_change_pct']}% higher."
        )
    elif changes["demand_change_pct"] < 0:
        parts.append(
            f"Demand was simulated {abs(changes['demand_change_pct'])}% lower."
        )

    if changes["inventory_change_pct"] < 0:
        parts.append(
            f"Inventory was simulated "
            f"{abs(changes['inventory_change_pct'])}% lower."
        )
    elif changes["inventory_change_pct"] > 0:
        parts.append(
            f"Inventory was simulated "
            f"{changes['inventory_change_pct']}% higher."
        )

    if changes["engagement_change_pct"] != 0:
        direction = (
            "higher"
            if changes["engagement_change_pct"] > 0
            else "lower"
        )
        parts.append(
            f"Engagement was simulated "
            f"{abs(changes['engagement_change_pct'])}% {direction}."
        )

    if changes["conversion_change_pct"] != 0:
        direction = (
            "higher"
            if changes["conversion_change_pct"] > 0
            else "lower"
        )
        parts.append(
            f"Conversion was simulated "
            f"{abs(changes['conversion_change_pct'])}% {direction}."
        )

    baseline_overall = baseline["overall_signal_score"]
    scenario_overall = scenario["overall_signal_score"]

    change = round(scenario_overall - baseline_overall, 2)

    if change > 0:
        parts.append(
            f"The overall signal increased by {change} points."
        )
    elif change < 0:
        parts.append(
            f"The overall signal decreased by {abs(change)} points."
        )
    else:
        parts.append(
            "The overall signal remained unchanged."
        )

    parts.append(
        f"Recommended action: {recommendation['action']}."
    )

    parts.append(recommendation["reason"])

    return " ".join(parts)


def run_scenario(
    df: pd.DataFrame,
    demand_change_pct: float = 0,
    inventory_change_pct: float = 0,
    engagement_change_pct: float = 0,
    conversion_change_pct: float = 0,
) -> dict[str, Any]:
    """
    Run a heuristic what-if scenario against a unified dataset.

    Important:
    This function performs scenario simulation.
    It does NOT estimate causal effects or forecast actual outcomes.
    """

    validate_change(
        demand_change_pct,
        "demand_change_pct",
    )

    validate_change(
        inventory_change_pct,
        "inventory_change_pct",
    )

    validate_change(
        engagement_change_pct,
        "engagement_change_pct",
    )

    validate_change(
        conversion_change_pct,
        "conversion_change_pct",
    )

    baseline = build_scorecard(df)

    baseline_demand = baseline[
        "demand_pressure_score"
    ]

    baseline_stock = baseline[
        "stock_risk_score"
    ]

    baseline_engagement = baseline[
        "engagement_momentum_score"
    ]

    baseline_conversion = baseline[
        "conversion_strength_score"
    ]

    scenario_demand = apply_positive_signal_change(
        baseline_demand,
        demand_change_pct,
    )

    scenario_stock = apply_inventory_change(
        baseline_stock,
        inventory_change_pct,
    )

    scenario_engagement = apply_positive_signal_change(
        baseline_engagement,
        engagement_change_pct,
    )

    scenario_conversion = apply_positive_signal_change(
        baseline_conversion,
        conversion_change_pct,
    )

    scenario_overall = calculate_overall_signal(
        scenario_demand,
        scenario_stock,
        scenario_engagement,
        scenario_conversion,
    )

    recommendation = generate_recommendation(
        scenario_demand,
        scenario_stock,
        scenario_engagement,
        scenario_conversion,
        scenario_overall,
    )

    scenario_confidence = determine_scenario_confidence(
        demand_change_pct,
        inventory_change_pct,
        engagement_change_pct,
        conversion_change_pct,
    )

    scenario_result = {
        "demand_pressure_score": scenario_demand,
        "stock_risk_score": scenario_stock,
        "engagement_momentum_score": scenario_engagement,
        "conversion_strength_score": scenario_conversion,
        "overall_signal_score": scenario_overall,
    }

    assumptions = {
        "demand_change_pct": demand_change_pct,
        "inventory_change_pct": inventory_change_pct,
        "engagement_change_pct": engagement_change_pct,
        "conversion_change_pct": conversion_change_pct,
    }

    comparison = {
        "demand_pressure": compare_metric(
            baseline_demand,
            scenario_demand,
        ),
        "stock_risk": compare_metric(
            baseline_stock,
            scenario_stock,
        ),
        "engagement_momentum": compare_metric(
            baseline_engagement,
            scenario_engagement,
        ),
        "conversion_strength": compare_metric(
            baseline_conversion,
            scenario_conversion,
        ),
        "overall_signal": compare_metric(
            baseline["overall_signal_score"],
            scenario_overall,
        ),
    }

    explanation = build_scenario_explanation(
        baseline,
        scenario_result,
        recommendation,
        assumptions,
    )

    return {
        "analysis_type": "heuristic_scenario_simulation",
        "assumptions": assumptions,
        "baseline": baseline,
        "scenario": scenario_result,
        "comparison": comparison,
        "recommendation": recommendation,
        "scenario_confidence": scenario_confidence,
        "explanation": explanation,
        "methodology_note": (
            "This output is a structured what-if simulation. "
            "It is not a forecast or causal effect estimate."
        ),
    }