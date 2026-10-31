from __future__ import annotations

from typing import Any
import pandas as pd

REQUIRED_COLUMNS = ("date", "sku_id", "units_sold", "engagement_rate")


def profile_unified_data(df: pd.DataFrame) -> dict[str, Any]:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame.")
    columns = list(df.columns)
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(columns))
    issues: list[dict[str, str]] = []

    def issue(code: str, severity: str, detail: str) -> None:
        issues.append({"code": code, "severity": severity, "detail": detail})

    result: dict[str, Any] = {
        "week": 14,
        "analysis_type": "unified_data_preflight",
        "rows": int(len(df)),
        "columns": columns,
        "required_columns_missing": missing_columns,
        "unique_skus": None,
        "date_min": None,
        "date_max": None,
        "duplicate_sku_dates": None,
        "invalid_or_missing": {},
        "next_calendar_day_pairs": None,
        "candidate_causal_rows": None,
        "engagement_unique_values": None,
        "issues": issues,
        "model_run_guidance": "blocked",
        "interpretation_boundary": (
            "Preflight checks describe data availability and structure only. "
            "Passing checks does not prove causal identification, statistical power, "
            "diagnostic validity, or business decision readiness."
        ),
    }
    if df.empty:
        issue("empty_dataset", "blocker", "No observations were supplied.")
    if missing_columns:
        issue("missing_columns", "blocker", "Missing required columns: " + ", ".join(missing_columns))
        return result
    if df.empty:
        return result

    dates = pd.to_datetime(df["date"], errors="coerce")
    skus = df["sku_id"].astype("string").str.strip()
    skus = skus.mask(skus.eq(""))
    units = pd.to_numeric(df["units_sold"], errors="coerce")
    engagement = pd.to_numeric(df["engagement_rate"], errors="coerce")
    for name, series in (("date", dates), ("sku_id", skus), ("units_sold", units), ("engagement_rate", engagement)):
        count = int(series.isna().sum())
        result["invalid_or_missing"][name] = count
        if count:
            issue("invalid_" + name, "warning", f"{count} row(s) have missing or invalid {name}.")

    clean = pd.DataFrame({"date": dates, "sku_id": skus, "units_sold": units, "engagement_rate": engagement}).dropna()
    result["unique_skus"] = int(clean["sku_id"].nunique())
    result["engagement_unique_values"] = int(clean["engagement_rate"].nunique())
    if not clean.empty:
        result["date_min"] = clean["date"].min().date().isoformat()
        result["date_max"] = clean["date"].max().date().isoformat()
        duplicates = int(clean.duplicated(["sku_id", "date"], keep=False).sum())
        result["duplicate_sku_dates"] = duplicates
        if duplicates:
            issue("duplicate_sku_dates", "warning", f"{duplicates} rows share a SKU/date with another row; temporal ordering may be ambiguous.")
        clean = clean.sort_values(["sku_id", "date"]).copy()
        group = clean.groupby("sku_id", sort=False)
        prior_units = group["units_sold"].shift(1)
        next_date = group["date"].shift(-1)
        next_units = group["units_sold"].shift(-1)
        next_day = (next_date - clean["date"]).dt.days.eq(1)
        result["next_calendar_day_pairs"] = int(next_day.sum())
        result["candidate_causal_rows"] = int((next_day & next_units.notna() & prior_units.notna()).sum())
    else:
        result["duplicate_sku_dates"] = 0
        result["next_calendar_day_pairs"] = 0
        result["candidate_causal_rows"] = 0

    if result["candidate_causal_rows"] == 0:
        issue("no_candidate_causal_rows", "warning", "No rows have both prior sales and next-calendar-day sales within a SKU.")
    if result["unique_skus"] < 2:
        issue("few_skus", "warning", "Fewer than two usable SKUs; SKU-cluster uncertainty may be unavailable.")
    if result["engagement_unique_values"] < 2:
        issue("no_treatment_variation", "warning", "Fewer than two distinct usable engagement values.")
    result["model_run_guidance"] = "requires_review" if issues else "candidate_for_exploratory_run"
    return result