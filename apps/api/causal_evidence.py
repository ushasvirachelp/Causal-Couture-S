from typing import Any


def build_causal_evidence_summary(
    estimate: dict[str, Any],
    uncertainty: dict[str, Any],
    placebo: dict[str, Any],
    overlap: dict[str, Any],
    stockout: dict[str, Any],
) -> dict[str, Any]:
    """
    Combine Phase 5 estimation and diagnostic outputs into a
    transparent evidence summary.

    This does NOT determine whether causality has been proven.
    It summarizes whether the current observational estimate
    passes several basic credibility checks.
    """

    checks = []

    # ---------------------------------------------------------
    # 1. ESTIMATOR STATUS
    # ---------------------------------------------------------

    estimate_ok = (
        estimate.get("status") == "estimated"
        and estimate.get("estimated_engagement_effect") is not None
    )

    checks.append(
        {
            "check": "effect_estimated",
            "passed": estimate_ok,
            "detail": (
                "The adjusted effect model produced an estimate."
                if estimate_ok
                else "The adjusted effect model did not produce a usable estimate."
            ),
        }
    )

    effect = estimate.get(
        "estimated_engagement_effect"
    )

    # ---------------------------------------------------------
    # 2. BOOTSTRAP UNCERTAINTY
    # ---------------------------------------------------------

    uncertainty_ok = (
        uncertainty.get("status") == "estimated"
        and isinstance(
            uncertainty.get("confidence_interval_95"),
            dict,
        )
    )

    ci_excludes_zero = False
    ci_lower = None
    ci_upper = None

    if uncertainty_ok:
        ci = uncertainty[
            "confidence_interval_95"
        ]

        ci_lower = ci.get("lower")
        ci_upper = ci.get("upper")

        if (
            ci_lower is not None
            and ci_upper is not None
        ):
            ci_excludes_zero = (
                ci_lower > 0
                or ci_upper < 0
            )

    checks.append(
        {
            "check": "bootstrap_uncertainty_available",
            "passed": uncertainty_ok,
            "detail": (
                "Bootstrap uncertainty estimates are available."
                if uncertainty_ok
                else "Bootstrap uncertainty could not be estimated reliably."
            ),
        }
    )

    checks.append(
        {
            "check": "confidence_interval_excludes_zero",
            "passed": ci_excludes_zero,
            "detail": (
                "The current 95% bootstrap interval does not include zero."
                if ci_excludes_zero
                else (
                    "The current 95% bootstrap interval includes zero "
                    "or is unavailable."
                )
            ),
        }
    )

    # ---------------------------------------------------------
    # 3. PLACEBO CHECK
    # ---------------------------------------------------------

    placebo_ok = (
        placebo.get("status") == "estimated"
        and placebo.get("placebo_effect") is not None
        and effect is not None
    )

    placebo_weaker = False

    if placebo_ok:
        original_abs = abs(
            float(effect)
        )

        placebo_abs = abs(
            float(
                placebo["placebo_effect"]
            )
        )

        placebo_weaker = (
            placebo_abs < original_abs
        )

    checks.append(
        {
            "check": "placebo_weaker_than_original",
            "passed": placebo_weaker,
            "detail": (
                "The shuffled-treatment placebo effect is weaker "
                "than the original estimate."
                if placebo_weaker
                else (
                    "The placebo estimate is not clearly weaker "
                    "than the original estimate."
                )
            ),
        }
    )

    # ---------------------------------------------------------
    # 4. TREATMENT VARIATION / OVERLAP
    # ---------------------------------------------------------

    overlap_status = overlap.get(
        "overlap_status"
    )

    overlap_ok = (
        overlap.get("status") == "analyzed"
        and overlap_status != "poor"
    )

    checks.append(
        {
            "check": "treatment_variation",
            "passed": overlap_ok,
            "detail": (
                "Observed engagement contains usable variation."
                if overlap_ok
                else (
                    "Observed engagement variation may be too limited "
                    "for reliable comparisons."
                )
            ),
        }
    )

    # ---------------------------------------------------------
    # 5. INVENTORY / STOCKOUT RISK
    # ---------------------------------------------------------

    stockout_level = (
        stockout
        .get(
            "suppressed_demand_risk",
            {},
        )
        .get(
            "level"
        )
    )

    inventory_ok = (
        stockout.get("status") == "analyzed"
        and stockout_level in {
            "LOW",
            "MODERATE",
        }
    )

    checks.append(
        {
            "check": "inventory_constraint_risk",
            "passed": inventory_ok,
            "detail": (
                "Inventory suppression risk is not currently classified as high."
                if inventory_ok
                else (
                    "Inventory constraints may materially suppress observed sales."
                )
            ),
        }
    )

    # ---------------------------------------------------------
    # EVIDENCE SCORE
    # ---------------------------------------------------------

    total_checks = len(checks)

    passed_checks = sum(
        1
        for check in checks
        if check["passed"]
    )

    evidence_score = (
        passed_checks
        / total_checks
        * 100
        if total_checks
        else 0
    )

    # Do not present this as a probability of causality.
    if evidence_score >= 80:
        evidence_level = "STRONGER_OBSERVATIONAL_SUPPORT"

    elif evidence_score >= 60:
        evidence_level = "MODERATE_OBSERVATIONAL_SUPPORT"

    elif evidence_score >= 40:
        evidence_level = "WEAK_OBSERVATIONAL_SUPPORT"

    else:
        evidence_level = "INSUFFICIENT_OBSERVATIONAL_SUPPORT"

    # ---------------------------------------------------------
    # EFFECT DIRECTION
    # ---------------------------------------------------------

    if effect is None:
        effect_direction = "unknown"

    elif effect > 0:
        effect_direction = "positive"

    elif effect < 0:
        effect_direction = "negative"

    else:
        effect_direction = "neutral"

    # ---------------------------------------------------------
    # FINAL SUMMARY
    # ---------------------------------------------------------

    return {
        "status": "evaluated",
        "estimated_effect": effect,
        "effect_direction": effect_direction,
        "confidence_interval_95": {
            "lower": ci_lower,
            "upper": ci_upper,
        },
        "checks_passed": int(
            passed_checks
        ),
        "checks_total": int(
            total_checks
        ),
        "evidence_score": round(
            evidence_score,
            1,
        ),
        "evidence_level": evidence_level,
        "checks": checks,
        "interpretation": (
            "This score summarizes the current observational evidence "
            "and diagnostic checks. It is not a probability that the "
            "effect is causal and should not be interpreted as causal proof."
        ),
        "causal_readiness_note": (
            "Stronger causal claims require defensible identification "
            "assumptions, adequate confounder measurement, temporal validity, "
            "treatment overlap, robustness checks, and sensitivity to "
            "alternative model specifications."
        ),
    }