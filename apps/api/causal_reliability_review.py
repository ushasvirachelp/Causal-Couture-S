"""Week 10: conservative reconciliation of existing Phase 5 diagnostics.

This module does NOT fit a new causal model or turn diagnostics into proof.
It summarizes reported diagnostic statuses and surfaces disagreements or
missing evidence for a human analyst to review.
"""
from __future__ import annotations
from typing import Any
import math

DIAGNOSTICS = (
    ("row_bootstrap", "uncertainty"),
    ("sku_cluster_bootstrap", "cluster_uncertainty"),
    ("shuffled_placebo", "placebo_test"),
    ("temporal_placebo", "temporal_placebo_test"),
    ("confounding_sensitivity", "unobserved_confounding_sensitivity"),
    ("treatment_overlap", "overlap_diagnostic"),
    ("stockout", "stockout_diagnostic"),
    ("model_robustness", "robustness_diagnostic"),
    ("evidence_summary", "evidence_summary"),
)


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def build_causal_reliability_review(intelligence: dict[str, Any]) -> dict[str, Any]:
    """Summarize Week 9 outputs without asserting unmeasured statistical claims."""
    if not isinstance(intelligence, dict):
        raise TypeError("Causal intelligence must be a dictionary.")

    estimate = intelligence.get("estimate")
    estimate = estimate if isinstance(estimate, dict) else {}
    effect = _finite_number(intelligence.get("estimated_effect"))
    if effect is None:
        effect = _finite_number(estimate.get("estimated_engagement_effect"))

    components: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    unavailable: list[str] = []
    for name, field in DIAGNOSTICS:
        payload = intelligence.get(field)
        if not isinstance(payload, dict):
            status = "missing"
            note = "Diagnostic result is absent or not structured as expected."
        else:
            status = str(payload.get("status") or "status_not_reported")
            note = str(payload.get("reason") or payload.get("error") or "")
        if status == "diagnostic_error":
            errors.append(name)
            category = "needs_attention"
        elif status in {"missing", "status_not_reported", "insufficient_data", "insufficient_clusters", "baseline_not_estimated", "insufficient_variation", "missing_columns", "not_estimated"}:
            unavailable.append(name)
            category = "inconclusive"
        else:
            # Executing successfully is NOT equivalent to supporting causality.
            category = "requires_interpretation"
        components[name] = {"status": status, "review_category": category, "note": note}

    sensitivity = intelligence.get("unobserved_confounding_sensitivity")
    sensitivity = sensitivity if isinstance(sensitivity, dict) else {}
    sensitivity_outcome = sensitivity.get("overall_diagnostic")
    direction_change = sensitivity.get("first_direction_change")
    if direction_change is None:
        for entry in sensitivity.get("stress_results", []):
            if isinstance(entry, dict) and entry.get("direction_changed") is True:
                direction_change = entry.get("stress_level") or "unspecified"
                break

    caution_flags: list[str] = []
    if direction_change is not None or sensitivity_outcome == "direction_sensitive_under_simulated_confounding":
        caution_flags.append("Engagement effect changes direction under at least one synthetic-confounding stress scenario.")
    if errors:
        caution_flags.append("Some secondary diagnostics failed; do not treat missing outputs as reassuring evidence.")
    if effect is None:
        caution_flags.append("A usable primary engagement effect was not reported.")

    follow_ups: list[str] = []
    if errors:
        follow_ups.append("Inspect diagnostic_error messages and classify implementation versus data limitations.")
    if unavailable:
        follow_ups.append("Document insufficient or missing diagnostic results without assigning favorable evidence.")
    if direction_change is not None:
        follow_ups.append("Review the first synthetic stress level where the effect direction changed.")
    follow_ups.append("Compare placebo coefficients and bootstrap intervals manually before drawing any business conclusions.")

    return {
        "week": 10,
        "analysis_type": "causal_reliability_review",
        "status": "requires_follow_up" if (errors or unavailable or effect is None) else "review_ready",
        "primary_effect": effect,
        "components": components,
        "counts": {"total": len(DIAGNOSTICS), "diagnostic_errors": len(errors), "unavailable_or_inconclusive": len(unavailable)},
        "diagnostic_errors": errors,
        "unavailable_diagnostics": unavailable,
        "confounding_sensitivity": {
            "status": sensitivity.get("status", "missing"),
            "overall_diagnostic": sensitivity_outcome,
            "first_direction_change": direction_change,
            "interpretation": (
                "A direction change is a caution signal within the simulated scenarios, not a measured amount of actual hidden confounding."
                if direction_change is not None else
                "No direction change was reported; this does not establish that unobserved confounding is absent."
            ),
        },
        "caution_flags": caution_flags,
        "follow_up_priorities": follow_ups,
        "interpretation_boundary": (
            "This is a descriptive review of observational diagnostics. It does not "
            "assign a causal probability, infer a treatment recommendation, or "
            "replace expert interpretation of effect sizes, placebo results, and uncertainty."
        ),
    }
