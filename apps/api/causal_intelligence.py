from typing import Any

import pandas as pd

from causal_dataset import build_causal_dataset, get_causal_dataset_summary
from causal_estimator import estimate_engagement_effect
from causal_validation import bootstrap_engagement_effect, run_placebo_test
from causal_cluster_bootstrap import cluster_bootstrap_engagement_effect
from causal_temporal_placebo import run_temporal_placebo_test
from causal_overlap import analyze_treatment_overlap
from causal_stockout import analyze_stockout_bias, add_inventory_demand_status
from causal_evidence import build_causal_evidence_summary
from causal_robustness import run_robustness_checks


def build_causal_intelligence(df: pd.DataFrame) -> dict[str, Any]:
    """
    Build the complete Phase 5 causal-intelligence response for:
    social engagement at time t -> product sales on the next calendar day.

    This remains observational causal analysis and does not constitute
    experimental proof of causation.
    """
    causal_df = build_causal_dataset(df)
    causal_df = add_inventory_demand_status(causal_df)
    dataset_summary = get_causal_dataset_summary(causal_df)

    estimate = estimate_engagement_effect(causal_df)

    uncertainty = bootstrap_engagement_effect(
        causal_df, estimate_engagement_effect
    )
    cluster_uncertainty = cluster_bootstrap_engagement_effect(
        causal_df, estimate_engagement_effect
    )

    placebo = run_placebo_test(causal_df)
    temporal_placebo = run_temporal_placebo_test(causal_df)
    overlap = analyze_treatment_overlap(causal_df)
    stockout = analyze_stockout_bias(causal_df)
    robustness = run_robustness_checks(causal_df)

    # Preserve the existing evidence-score contract. The temporal placebo
    # is exposed separately rather than silently changing the heuristic score.
    evidence = build_causal_evidence_summary(
        estimate=estimate,
        uncertainty=uncertainty,
        placebo=placebo,
        overlap=overlap,
        stockout=stockout,
    )

    estimated_effect = estimate.get("estimated_engagement_effect")
    effect_per_10pct = (
        float(estimated_effect) * 0.10
        if estimated_effect is not None
        else None
    )

    if estimated_effect is None:
        effect_direction = "unknown"
        executive_summary = (
            "The current dataset does not provide enough usable "
            "information to estimate the engagement effect."
        )
    elif estimated_effect > 0:
        effect_direction = "positive"
        executive_summary = (
            "The current observational model estimates a positive "
            "relationship between social engagement and next-day "
            "product sales after adjustment for available historical, "
            "inventory, product, and time-related factors."
        )
    elif estimated_effect < 0:
        effect_direction = "negative"
        executive_summary = (
            "The current observational model estimates a negative "
            "relationship between social engagement and next-day "
            "product sales after adjustment for available historical, "
            "inventory, product, and time-related factors."
        )
    else:
        effect_direction = "neutral"
        executive_summary = (
            "The current observational model estimates little or no "
            "change in next-day product sales associated with social "
            "engagement."
        )

    return {
        "phase": "Phase 5",
        "analysis_type": "causal_intelligence",
        "causal_question": (
            "What is the causal effect of social engagement "
            "on subsequent product sales?"
        ),
        "treatment": "engagement_rate_t",
        "outcome": "units_sold_next_day",
        "executive_summary": executive_summary,
        "effect_direction": effect_direction,
        "estimated_effect": (
            round(float(estimated_effect), 6)
            if estimated_effect is not None else None
        ),
        "estimated_effect_per_10_percentage_point_engagement_increase": (
            round(effect_per_10pct, 6)
            if effect_per_10pct is not None else None
        ),
        "dataset": dataset_summary,
        "estimate": estimate,
        "uncertainty": uncertainty,
        "cluster_uncertainty": cluster_uncertainty,
        "placebo_test": placebo,
        "temporal_placebo_test": temporal_placebo,
        "overlap_diagnostic": overlap,
        "stockout_diagnostic": stockout,
        "robustness_diagnostic": robustness,
        "evidence_summary": evidence,
        "methodology": {
            "data_type": "observational",
            "temporal_structure": (
                "engagement at time t -> sales on next calendar day"
            ),
            "current_adjustment_strategy": [
                "prior sales",
                "prior engagement",
                "inventory availability",
                "SKU fixed effects",
                "day-of-week effects",
            ],
            "uncertainty_strategy": (
                "Both row-level bootstrap uncertainty and SKU-level "
                "cluster-bootstrap uncertainty are reported."
            ),
            "temporal_falsification_strategy": (
                "Future next-calendar-day engagement is tested against "
                "current sales as a negative-control exposure. Because "
                "future engagement cannot cause past sales, a large "
                "temporal-placebo coefficient is treated as a warning "
                "signal rather than causal evidence."
            ),
            "web_variables": (
                "Product views and conversion variables are not "
                "automatically controlled because they may lie on "
                "the pathway between engagement and purchase."
            ),
            "inventory_boundary": (
                "Periods with zero inventory are excluded from the "
                "primary estimator, while broader low-stock conditions "
                "are reported separately as suppressed-demand risk."
            ),
        },
        "causal_warning": (
            "This is an observational causal-analysis pipeline. "
            "The estimate depends on the stated DAG and identification "
            "assumptions and should not be interpreted as experimental "
            "proof that social engagement causes sales. The diagnostics "
            "improve transparency but do not establish causal identification."
        ),
    }
