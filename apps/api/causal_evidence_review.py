"""Week 12: reproducible, conservative review of existing Phase 5 outputs.

Consumes the actual dictionary returned by build_causal_intelligence; does not
fit a model or make claims of causal identification or business readiness.
Standard-library only; safe to use on a previously saved JSON response.
"""
from __future__ import annotations

import math
from typing import Any

# These keys match the current Phase 5 causal_intelligence.py response.
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

INCONCLUSIVE_STATUSES = {
    "missing", "status_not_reported", "insufficient_data", "insufficient_clusters",
    "insufficient_bootstrap_estimates", "insufficient_bootstrap_samples",
    "baseline_not_estimated", "insufficient_variation", "missing_columns",
    "not_estimated", "inventory_data_unavailable", "insufficient_inventory_data",
    "not_assessable", "unavailable", "skipped",
}
AVAILABLE_STATUSES = {"estimated", "analyzed", "completed", "ok", "success"}


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _interval(payload: dict[str, Any]) -> tuple[float, float] | None:
    """Actual project intervals use {'lower': number, 'upper': number}."""
    raw = payload.get("confidence_interval_95")
    if isinstance(raw, dict):
        lower, upper = _finite_number(raw.get("lower")), _finite_number(raw.get("upper"))
    elif isinstance(raw, (list, tuple)) and len(raw) == 2:
        lower, upper = _finite_number(raw[0]), _finite_number(raw[1])
    else:
        return None
    if lower is None or upper is None or lower > upper:
        return None
    return lower, upper


def _signal(status: str) -> str:
    if status == "diagnostic_error":
        return "error"
    if status in INCONCLUSIVE_STATUSES:
        return "inconclusive"
    if status in AVAILABLE_STATUSES:
        return "available_requires_interpretation"
    return "unknown_status_requires_review"


def build_week12_evidence_review(intelligence: dict[str, Any]) -> dict[str, Any]:
    """Return a transparent audit of reported results; never assert a causal pass."""
    if not isinstance(intelligence, dict):
        raise TypeError("Expected a Phase 5 causal-intelligence JSON object.")

    primary = _finite_number(intelligence.get("estimated_effect"))
    estimate = intelligence.get("estimate")
    if primary is None and isinstance(estimate, dict):
        primary = _finite_number(estimate.get("estimated_engagement_effect"))

    diagnostics: list[dict[str, Any]] = []
    incomplete: list[str] = []
    errors: list[str] = []
    unknown: list[str] = []
    for name, key in DIAGNOSTICS:
        payload = intelligence.get(key)
        if not isinstance(payload, dict):
            payload = {}
        status = str(payload.get("status") or "missing")
        signal = _signal(status)
        if signal == "error":
            errors.append(name)
        elif signal == "inconclusive":
            incomplete.append(name)
        elif signal == "unknown_status_requires_review":
            unknown.append(name)
        diagnostics.append({
            "diagnostic": name,
            "status": status,
            "evidence_signal": signal,
            "detail": str(payload.get("reason") or payload.get("error") or payload.get("message") or ""),
        })

    flags: list[dict[str, str]] = []
    review_items: list[str] = []

    def flag(code: str, description: str) -> None:
        flags.append({"code": code, "finding": description})

    row = intelligence.get("uncertainty")
    cluster = intelligence.get("cluster_uncertainty")
    row = row if isinstance(row, dict) else {}
    cluster = cluster if isinstance(cluster, dict) else {}
    row_ci, cluster_ci = _interval(row), _interval(cluster)
    if row_ci and cluster_ci:
        row_excludes_zero = row_ci[0] > 0 or row_ci[1] < 0
        cluster_excludes_zero = cluster_ci[0] > 0 or cluster_ci[1] < 0
        if row_excludes_zero != cluster_excludes_zero:
            flag("bootstrap_interval_disagreement", "Row and SKU-cluster 95% intervals differ in whether they contain zero.")
        review_items.append("Review both row and SKU-cluster bootstrap intervals; SKU observations may be dependent.")
    else:
        review_items.append("At least one bootstrap interval is unavailable or unrecognized; do not infer agreement.")

    sensitivity = intelligence.get("unobserved_confounding_sensitivity")
    sensitivity = sensitivity if isinstance(sensitivity, dict) else {}
    first_change = sensitivity.get("first_direction_change")
    if first_change is None:
        entries = sensitivity.get("stress_results")
        if isinstance(entries, list):
            first_change = next((e.get("stress_level") or "unspecified" for e in entries
                                 if isinstance(e, dict) and e.get("direction_changed") is True), None)
    if first_change is not None or sensitivity.get("overall_diagnostic") == "direction_sensitive_under_simulated_confounding":
        flag("synthetic_confounding_direction_change", "Effect direction changed under at least one hypothetical confounding stress scenario.")
    review_items.append("Synthetic confounding stress levels are heuristic and do not measure actual hidden confounding.")

    overlap = intelligence.get("overlap_diagnostic")
    overlap = overlap if isinstance(overlap, dict) else {}
    if overlap.get("overlap_status") == "poor":
        flag("poor_treatment_variation", "Treatment overlap diagnostic reports poor observed engagement variation.")
    elif overlap.get("overlap_status") == "review":
        review_items.append("Inspect treatment distribution: observed variation alone does not prove positivity.")

    stockout = intelligence.get("stockout_diagnostic")
    stockout = stockout if isinstance(stockout, dict) else {}
    risk = stockout.get("suppressed_demand_risk")
    risk = risk if isinstance(risk, dict) else {}
    if str(risk.get("level", "")).upper() in {"MODERATE", "HIGH"}:
        flag("inventory_pressure", "Inventory pressure may suppress observed sales; see stockout diagnostic.")

    shuffled = intelligence.get("placebo_test")
    temporal = intelligence.get("temporal_placebo_test")
    shuffled = shuffled if isinstance(shuffled, dict) else {}
    temporal = temporal if isinstance(temporal, dict) else {}
    shuffled_effect = _finite_number(shuffled.get("placebo_effect"))
    temporal_effect = _finite_number(temporal.get("temporal_placebo_effect"))
    if shuffled_effect is not None or temporal_effect is not None:
        review_items.append("Inspect placebo coefficients relative to primary estimate and their designs; no automatic placebo pass/fail threshold is applied.")

    if primary is None:
        flag("missing_primary_effect", "No finite primary engagement-effect estimate was reported.")
    if errors:
        flag("diagnostic_execution_errors", "One or more diagnostics returned execution errors.")
    if incomplete:
        flag("inconclusive_diagnostics", "One or more diagnostics are unavailable or inconclusive.")
    if unknown:
        flag("unrecognized_diagnostic_status", "One or more diagnostic statuses are not recognized; review them manually.")

    if primary is None or errors or incomplete or unknown:
        readiness = "insufficient_evidence_for_decision"
    elif flags:
        readiness = "analyst_review_required"
    else:
        readiness = "exploratory_interpretation_only"

    return {
        "week": 12,
        "analysis_type": "causal_evidence_review",
        "primary_observational_effect": primary,
        "decision_readiness": readiness,
        "diagnostics": diagnostics,
        "diagnostic_counts": {
            "total": len(DIAGNOSTICS),
            "errors": len(errors),
            "inconclusive": len(incomplete),
            "unknown_status": len(unknown),
        },
        "bootstrap_intervals_95": {
            "row": list(row_ci) if row_ci else None,
            "sku_cluster": list(cluster_ci) if cluster_ci else None,
        },
        "placebo_coefficients": {
            "shuffled_treatment": shuffled_effect,
            "future_engagement_to_current_sales": temporal_effect,
        },
        "caution_flags": flags,
        "analyst_follow_ups": list(dict.fromkeys(review_items)),
        "interpretation_boundary": (
            "Rule-based audit of observational diagnostics, not an estimate of causal certainty, "
            "a statistical validation certificate, or authorization for automatic retail actions. "
            "Missing results and unrecognized statuses are not treated as favorable evidence."
        ),
    }


def render_week12_markdown(review: dict[str, Any], source_label: str = "unspecified") -> str:
    """Make a readable, reproducible report from the structured review."""
    lines = [
        "# Causal Couture — Week 12 Evidence Review",
        "",
        f"**Source:** `{source_label.replace('`', '')}`",
        "**Phase:** 5 — Causal Intelligence",
        "**Review type:** Observational evidence audit (not experimental proof)",
        "",
        "## Summary",
        "",
        f"- Primary observational engagement effect: `{review.get('primary_observational_effect')}`",
        f"- Decision-readiness category: **{review['decision_readiness']}**",
        "- No automatic marketing, inventory, or pricing decision is authorized by this category.",
        "",
        "## Diagnostic inventory",
        "",
        "| Diagnostic | Execution status | Evidence signal |",
        "| --- | --- | --- |",
    ]
    for item in review["diagnostics"]:
        lines.append(f"| {item['diagnostic']} | {item['status']} | {item['evidence_signal']} |")
    lines += ["", "## Evidence requiring attention", ""]
    flags = review["caution_flags"]
    if flags:
        lines += [f"- **{f['code']}:** {f['finding']}" for f in flags]
    else:
        lines.append("- No predefined warning was detected in the reported fields; this is not proof of causal identification.")
    lines += ["", "## Numerical context", ""]
    intervals = review["bootstrap_intervals_95"]
    lines.append(f"- Row bootstrap 95% interval: `{intervals['row']}`")
    lines.append(f"- SKU-cluster bootstrap 95% interval: `{intervals['sku_cluster']}`")
    placebo = review["placebo_coefficients"]
    lines.append(f"- Shuffled placebo coefficient: `{placebo['shuffled_treatment']}`")
    lines.append(f"- Temporal placebo coefficient: `{placebo['future_engagement_to_current_sales']}`")
    lines += ["", "## Analyst follow-ups", ""]
    lines += [f"- {item}" for item in review["analyst_follow_ups"]]
    lines += ["", "## Interpretation boundary", "", review["interpretation_boundary"], ""]
    return "\n".join(lines)
