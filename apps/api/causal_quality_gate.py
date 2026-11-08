from __future__ import annotations

from typing import Any
import math
import pandas as pd

REQUIRED = ("date", "sku_id", "units_sold", "engagement_rate")


def _number(value: Any) -> float | None:
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _summarize(series: pd.Series) -> dict[str, Any]:
    values = pd.to_numeric(series, errors="coerce")
    values = values[values.notna() & values.map(lambda x: math.isfinite(float(x)))]
    if values.empty:
        return {"count": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "count": int(len(values)), "mean": round(float(values.mean()), 6),
        "median": round(float(values.median()), 6),
        "min": round(float(values.min()), 6), "max": round(float(values.max()), 6),
    }


def analyze_quality(df: pd.DataFrame) -> dict[str, Any]:
    """Return (quality, per_sku_rows); strict windows require adjacent days on both sides."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame")
    issues: list[dict[str, str]] = []
    def add(code: str, severity: str, detail: str, action: str) -> None:
        issues.append({"code": code, "severity": severity, "detail": detail, "analyst_action": action})

    missing = sorted(set(REQUIRED) - set(df.columns))
    base: dict[str, Any] = {
        "week": 15, "analysis_type": "daily_sku_quality_gate",
        "required_columns": list(REQUIRED), "missing_columns": missing,
        "total_rows": int(len(df)), "columns": list(df.columns),
        "quality_gate": "blocked", "issues": issues,
        "invalid_counts": {}, "duplicate_key_rows": None, "duplicate_conflict_keys": None,
        "date_range": {"start": None, "end": None}, "unique_skus": 0,
        "next_day_pairs": 0, "phase5_like_candidate_rows": 0,
        "strict_three_day_windows": 0, "multi_day_gaps": 0,
        "attrition": [], "summary_statistics": {}, "per_sku": [],
        "analyst_actions": [],
        "interpretation_boundary": (
            "This is descriptive data-quality screening, not causal identification, "
            "model validation, or permission for automated business decisions. "
            "A passing quality gate is not a claim of sufficient statistical power."
        ),
    }
    if missing:
        add("missing_required_columns", "blocker", ", ".join(missing), "Supply a unified daily-SKU CSV with all required fields.")
        return base
    if df.empty:
        add("empty_dataset", "blocker", "The dataset contains zero rows.", "Supply observations before analysis.")
        return base

    date = pd.to_datetime(df["date"], errors="coerce", utc=True).dt.tz_localize(None).dt.normalize()
    sku = df["sku_id"].astype("string").str.strip()
    sku = sku.mask(sku.eq(""))
    units = pd.to_numeric(df["units_sold"], errors="coerce")
    engagement = pd.to_numeric(df["engagement_rate"], errors="coerce")
    units = units.mask(~units.map(lambda v: math.isfinite(float(v)) if pd.notna(v) else False))
    engagement = engagement.mask(~engagement.map(lambda v: math.isfinite(float(v)) if pd.notna(v) else False))
    bad_units = units.lt(0).fillna(False)
    bad_engagement = (~engagement.between(0, 1)) & engagement.notna()
    base["invalid_counts"] = {
        "date": int(date.isna().sum()), "sku_id": int(sku.isna().sum()),
        "units_sold": int(units.isna().sum()), "engagement_rate": int(engagement.isna().sum()),
        "negative_units_sold": int(bad_units.sum()),
        "engagement_outside_0_1": int(bad_engagement.sum()),
    }
    for key, count in base["invalid_counts"].items():
        if count:
            add("invalid_" + key, "warning", f"{count} row(s) affected.", "Inspect source ingestion and correct or exclude affected records.")

    work = pd.DataFrame({"date": date, "sku_id": sku, "units_sold": units, "engagement_rate": engagement})
    key_valid = work["date"].notna() & work["sku_id"].notna()
    numeric_valid = work["units_sold"].notna() & work["engagement_rate"].notna() & ~bad_units & ~bad_engagement
    clean = work[key_valid & numeric_valid].copy()
    duplicate = clean.duplicated(["sku_id", "date"], keep=False)
    duplicate_rows = clean[duplicate]
    base["duplicate_key_rows"] = int(duplicate.sum())
    if not duplicate_rows.empty:
        grouped_dupes = duplicate_rows.groupby(["sku_id", "date"], dropna=False)
        conflicts = grouped_dupes.agg({"units_sold": "nunique", "engagement_rate": "nunique"})
        base["duplicate_conflict_keys"] = int(((conflicts["units_sold"] > 1) | (conflicts["engagement_rate"] > 1)).sum())
        add("duplicate_sku_dates", "warning", f"{base['duplicate_key_rows']} row(s) have repeated SKU/date keys; {base['duplicate_conflict_keys']} key(s) have conflicting measurements.", "Resolve duplicates upstream; all duplicated keys are excluded from temporal counts.")
    else:
        base["duplicate_conflict_keys"] = 0
    clean = clean[~duplicate].sort_values(["sku_id", "date"]).copy()
    base["unique_skus"] = int(clean["sku_id"].nunique())
    if not clean.empty:
        base["date_range"] = {"start": clean["date"].min().date().isoformat(), "end": clean["date"].max().date().isoformat()}
    per_sku = []
    for sku_id, sub in clean.groupby("sku_id", sort=True):
        sub = sub.sort_values("date")
        days = sub["date"].diff().dt.days
        next_days = (sub["date"].shift(-1) - sub["date"]).dt.days
        next_day = next_days.eq(1)
        # The current Phase 5 builder uses previous *observation* for prior sales,
        # and requires next *calendar day* for the outcome.
        phase5 = next_day & sub["units_sold"].shift(1).notna()
        strict = next_day & days.eq(1)
        per_sku.append({
            "sku_id": str(sku_id), "usable_rows": int(len(sub)),
            "first_date": sub["date"].min().date().isoformat(),
            "last_date": sub["date"].max().date().isoformat(),
            "next_day_pairs": int(next_day.sum()),
            "phase5_like_candidates": int(phase5.sum()),
            "strict_three_day_windows": int(strict.sum()),
            "multi_day_gaps": int(days.gt(1).sum()),
            "engagement_distinct": int(sub["engagement_rate"].nunique()),
            "mean_units_sold": _summarize(sub["units_sold"])["mean"],
            "mean_engagement_rate": _summarize(sub["engagement_rate"])["mean"],
        })
    base["per_sku"] = per_sku
    for metric in ("next_day_pairs", "strict_three_day_windows", "multi_day_gaps"):
        base[metric] = sum(row[metric] for row in per_sku)
    base["phase5_like_candidate_rows"] = sum(row["phase5_like_candidates"] for row in per_sku)
    base["attrition"] = [
        {"stage": "Input rows", "rows": len(df)},
        {"stage": "Valid SKU/date keys", "rows": int(key_valid.sum())},
        {"stage": "Valid keys and numeric values", "rows": int((key_valid & numeric_valid).sum())},
        {"stage": "Unique, valid SKU/date rows", "rows": int(len(clean))},
        {"stage": "Phase 5-like candidate rows", "rows": base["phase5_like_candidate_rows"]},
        {"stage": "Strict three-day windows", "rows": base["strict_three_day_windows"]},
    ]
    base["summary_statistics"] = {
        "units_sold": _summarize(clean["units_sold"]),
        "engagement_rate": _summarize(clean["engagement_rate"]),
    }
    if not base["phase5_like_candidate_rows"]:
        add("no_phase5_candidates", "blocker", "No usable prior-observation/next-day sales pairs.", "Collect more consecutive daily observations per SKU.")
    if not base["strict_three_day_windows"]:
        add("no_strict_three_day_windows", "warning", "No fully consecutive three-day SKU windows.", "Inspect temporal gaps; the existing Phase 5 prior sales lag is previous observation, not always previous calendar day.")
    if base["multi_day_gaps"]:
        add("temporal_gaps", "warning", f"{base['multi_day_gaps']} multi-day gap(s) between SKU observations.", "Review date coverage before interpreting lag relationships.")
    if base["unique_skus"] < 2:
        add("few_skus", "warning", "Fewer than two usable SKUs.", "SKU-cluster bootstrap may not be informative or available.")
    if clean["engagement_rate"].nunique() < 2:
        add("no_engagement_variation", "warning", "Engagement rate does not vary across usable rows.", "Collect observations with measurable engagement variation.")
    blockers = [x for x in issues if x["severity"] == "blocker"]
    base["quality_gate"] = "blocked" if blockers else ("requires_review" if issues else "candidate_for_exploratory_analysis")
    base["analyst_actions"] = list(dict.fromkeys(x["analyst_action"] for x in issues)) or ["Review dataset provenance and downstream model diagnostics before any inference."]
    return base
