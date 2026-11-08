from __future__ import annotations
from typing import Any


def compare_profiles(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    if baseline.get("analysis_type") != "daily_sku_quality_gate" or current.get("analysis_type") != "daily_sku_quality_gate":
        raise ValueError("Both inputs must be Week 15 quality profiles")
    metrics = ("total_rows", "unique_skus", "next_day_pairs", "phase5_like_candidate_rows", "strict_three_day_windows", "multi_day_gaps", "duplicate_key_rows")
    changes = []
    for name in metrics:
        old, new = baseline.get(name), current.get(name)
        changes.append({"metric": name, "baseline": old, "current": new,
                        "absolute_change": (new - old) if isinstance(old, (int, float)) and isinstance(new, (int, float)) else None})
    for field in ("units_sold", "engagement_rate"):
        for stat in ("mean", "median"):
            old = baseline.get("summary_statistics", {}).get(field, {}).get(stat)
            new = current.get("summary_statistics", {}).get(field, {}).get(stat)
            changes.append({"metric": field + "_" + stat, "baseline": old, "current": new,
                            "absolute_change": round(new - old, 6) if isinstance(old, (int, float)) and isinstance(new, (int, float)) else None})
    old_skus = {row["sku_id"] for row in baseline.get("per_sku", [])}
    new_skus = {row["sku_id"] for row in current.get("per_sku", [])}
    return {
        "analysis_type": "descriptive_baseline_comparison",
        "baseline_gate": baseline.get("quality_gate"),
        "current_gate": current.get("quality_gate"),
        "sku_overlap_count": len(old_skus & new_skus),
        "sku_only_baseline_count": len(old_skus - new_skus),
        "sku_only_current_count": len(new_skus - old_skus),
        "baseline_date_range": baseline.get("date_range"),
        "current_date_range": current.get("date_range"),
        "metric_changes": changes,
        "interpretation_boundary": (
            "Differences are descriptive and may reflect different date ranges, SKU composition, "
            "data ingestion, or business conditions. No statistical drift significance, "
            "causal effect, or model degradation is inferred."
        ),
    }
