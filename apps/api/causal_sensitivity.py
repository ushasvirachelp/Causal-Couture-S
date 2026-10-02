from typing import Any
import numpy as np
import pandas as pd

def run_unobserved_confounding_sensitivity(
    df: pd.DataFrame,
    estimator_function,
    random_state: int = 42,
) -> dict[str, Any]:
    """Heuristic synthetic-confounder sensitivity stress test."""
    required=["engagement_rate_t","units_sold_next_day"]
    missing=[c for c in required if c not in df.columns]
    if missing:
        return {"status":"missing_columns","missing_columns":missing,
                "method":"synthetic_unobserved_confounding_stress_test"}

    working=df.copy()
    if "causal_row_valid" in working.columns:
        working=working[working["causal_row_valid"]==1].copy()
    if "inventory_constrained_flag" in working.columns:
        working=working[working["inventory_constrained_flag"]==0].copy()

    for c in required:
        working[c]=pd.to_numeric(working[c],errors="coerce")
    working=working.dropna(subset=required).copy()

    if len(working)<20:
        return {"status":"insufficient_data","rows_used":int(len(working)),
                "method":"synthetic_unobserved_confounding_stress_test",
                "reason":"At least 20 eligible rows are required."}

    baseline=estimator_function(working)
    baseline_effect=baseline.get("estimated_engagement_effect")
    if baseline.get("status")!="estimated" or baseline_effect is None:
        return {"status":"baseline_not_estimated",
                "method":"synthetic_unobserved_confounding_stress_test",
                "baseline":baseline}

    baseline_effect=float(baseline_effect)
    treatment=working["engagement_rate_t"].astype(float).to_numpy()
    outcome=working["units_sold_next_day"].astype(float).to_numpy()
    t_sd=float(np.std(treatment)); y_sd=float(np.std(outcome))
    if t_sd==0 or y_sd==0:
        return {"status":"insufficient_variation",
                "method":"synthetic_unobserved_confounding_stress_test",
                "treatment_std":t_sd,"outcome_std":y_sd}

    rng=np.random.default_rng(random_state)
    latent=rng.normal(0.0,1.0,size=len(working))
    levels=[("weak",0.10),("moderate",0.25),("strong",0.50),("very_strong",0.75)]
    results=[]

    for label,strength in levels:
        stressed=working.copy()
        stressed["engagement_rate_t"]=treatment-(strength*t_sd*latent)
        stressed["units_sold_next_day"]=outcome-(strength*y_sd*latent)
        estimate=estimator_function(stressed)
        effect=estimate.get("estimated_engagement_effect")
        if estimate.get("status")=="estimated" and effect is not None:
            effect=float(effect)
            change=abs(effect-baseline_effect)
            relative=change/abs(baseline_effect) if baseline_effect!=0 else None
            direction_changed=(np.sign(effect)!=np.sign(baseline_effect)
                               if baseline_effect!=0 and effect!=0 else False)
            results.append({
                "stress_level":label,
                "synthetic_confounding_strength":strength,
                "estimated_effect":round(effect,6),
                "absolute_change_from_baseline":round(change,6),
                "relative_change_from_baseline":round(float(relative),6) if relative is not None else None,
                "direction_changed":bool(direction_changed),
            })
        else:
            results.append({"stress_level":label,
                            "synthetic_confounding_strength":strength,
                            "status":estimate.get("status","not_estimated")})

    estimated=[r for r in results if "estimated_effect" in r]
    first_change=next((r["stress_level"] for r in estimated if r["direction_changed"]),None)
    overall=("not_assessable" if not estimated else
             "direction_sensitive_under_simulated_confounding" if first_change
             else "direction_stable_across_simulated_stress_levels")

    return {
        "status":"estimated",
        "method":"synthetic_unobserved_confounding_stress_test",
        "rows_used":int(len(working)),
        "baseline_effect":round(baseline_effect,6),
        "stress_results":results,
        "first_direction_change":first_change,
        "overall_diagnostic":overall,
        "interpretation":(
            "This diagnostic measures how the engagement coefficient changes "
            "under progressively stronger hypothetical hidden-confounding pressure. "
            "Greater stability is more reassuring, but the stress levels are not "
            "estimates of the true amount of unobserved confounding."
        ),
        "methodology_boundary":(
            "This is a heuristic sensitivity analysis, not a formal bound, "
            "probability of causality, or proof that unobserved confounding is absent."
        ),
    }
