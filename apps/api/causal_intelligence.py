from typing import Any, Callable
import pandas as pd
from causal_dataset import build_causal_dataset, get_causal_dataset_summary
from causal_estimator import estimate_engagement_effect
from causal_validation import bootstrap_engagement_effect, run_placebo_test
from causal_cluster_bootstrap import cluster_bootstrap_engagement_effect
from causal_temporal_placebo import run_temporal_placebo_test
from causal_sensitivity import run_unobserved_confounding_sensitivity
from causal_overlap import analyze_treatment_overlap
from causal_stockout import analyze_stockout_bias, add_inventory_demand_status
from causal_evidence import build_causal_evidence_summary
from causal_robustness import run_robustness_checks

def _safe_diagnostic(name: str, function: Callable, *args) -> dict[str, Any]:
    try:
        result=function(*args)
        if isinstance(result,dict):
            return result
        return {"status":"diagnostic_error","diagnostic":name,
                "error":"Diagnostic returned a non-dictionary result."}
    except Exception as exc:
        return {"status":"diagnostic_error","diagnostic":name,"error":str(exc)}

def build_causal_intelligence(df: pd.DataFrame) -> dict[str, Any]:
    causal_df=build_causal_dataset(df)
    causal_df=add_inventory_demand_status(causal_df)
    dataset_summary=get_causal_dataset_summary(causal_df)
    estimate=estimate_engagement_effect(causal_df)

    uncertainty=_safe_diagnostic("row_bootstrap",bootstrap_engagement_effect,
                                 causal_df,estimate_engagement_effect)
    cluster=_safe_diagnostic("sku_cluster_bootstrap",cluster_bootstrap_engagement_effect,
                             causal_df,estimate_engagement_effect)
    placebo=_safe_diagnostic("shuffled_placebo",run_placebo_test,causal_df)
    temporal=_safe_diagnostic("temporal_placebo",run_temporal_placebo_test,causal_df)
    sensitivity=_safe_diagnostic("unobserved_confounding_sensitivity",
                                 run_unobserved_confounding_sensitivity,
                                 causal_df,estimate_engagement_effect)
    overlap=_safe_diagnostic("overlap",analyze_treatment_overlap,causal_df)
    stockout=_safe_diagnostic("stockout",analyze_stockout_bias,causal_df)
    robustness=_safe_diagnostic("robustness",run_robustness_checks,causal_df)
    evidence=_safe_diagnostic("evidence_summary",build_causal_evidence_summary,
                              estimate,uncertainty,placebo,overlap,stockout)

    effect=estimate.get("estimated_engagement_effect")
    scaled=float(effect)*0.10 if effect is not None else None
    if effect is None:
        direction="unknown"; summary="The current dataset does not provide enough usable information to estimate the engagement effect."
    elif effect>0:
        direction="positive"; summary="The current observational model estimates a positive relationship between social engagement and next-day product sales after adjustment for available historical, inventory, product, and time-related factors."
    elif effect<0:
        direction="negative"; summary="The current observational model estimates a negative relationship between social engagement and next-day product sales after adjustment for available historical, inventory, product, and time-related factors."
    else:
        direction="neutral"; summary="The current observational model estimates little or no change in next-day product sales associated with social engagement."

    return {
        "phase":"Phase 5","analysis_type":"causal_intelligence",
        "causal_question":"What is the causal effect of social engagement on subsequent product sales?",
        "treatment":"engagement_rate_t","outcome":"units_sold_next_day",
        "executive_summary":summary,"effect_direction":direction,
        "estimated_effect":round(float(effect),6) if effect is not None else None,
        "estimated_effect_per_10_percentage_point_engagement_increase":round(scaled,6) if scaled is not None else None,
        "diagnostic_status":{
            "row_bootstrap":uncertainty.get("status"),
            "cluster_bootstrap":cluster.get("status"),
            "shuffled_placebo":placebo.get("status"),
            "temporal_placebo":temporal.get("status"),
            "confounding_sensitivity":sensitivity.get("status"),
            "overlap":overlap.get("status"),
            "stockout":stockout.get("status"),
            "robustness":robustness.get("status"),
            "evidence_summary":evidence.get("status"),
        },
        "dataset":dataset_summary,"estimate":estimate,
        "uncertainty":uncertainty,"cluster_uncertainty":cluster,
        "placebo_test":placebo,"temporal_placebo_test":temporal,
        "unobserved_confounding_sensitivity":sensitivity,
        "overlap_diagnostic":overlap,"stockout_diagnostic":stockout,
        "robustness_diagnostic":robustness,"evidence_summary":evidence,
        "methodology":{
            "data_type":"observational",
            "temporal_structure":"engagement at time t -> sales on next calendar day",
            "current_adjustment_strategy":["prior sales","prior engagement","inventory availability","SKU fixed effects","day-of-week effects"],
            "uncertainty_strategy":"Both row-level and SKU-level cluster-bootstrap uncertainty are reported.",
            "temporal_falsification_strategy":"Future next-calendar-day engagement is tested against current sales as a negative-control exposure.",
            "unobserved_confounding_strategy":"A synthetic-confounder stress test measures how the estimate changes under progressively stronger hypothetical omitted-confounding pressure. Stress levels are heuristic.",
            "diagnostic_isolation":"Secondary diagnostics execute independently so one diagnostic error is reported without crashing the consolidated response.",
        },
        "causal_warning":"This is observational causal analysis. The diagnostics improve transparency but do not establish experimental causal identification.",
    }
