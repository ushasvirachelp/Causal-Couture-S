"""Week 15 quality-intelligence CLI: no causal estimator or external service."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
import pandas as pd
from causal_quality_gate import analyze_quality
from causal_quality_comparison import compare_profiles
from causal_quality_dashboard import render_quality_html
from causal_evidence_review import build_week12_evidence_review

SKU_COLUMNS = ("sku_id", "usable_rows", "first_date", "last_date", "next_day_pairs", "phase5_like_candidates", "strict_three_day_windows", "multi_day_gaps", "engagement_distinct", "mean_units_sold", "mean_engagement_rate")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_quality_markdown(result: dict[str, Any]) -> str:
    p = result["quality_profile"]
    lines = ["# Causal Couture — Week 15 Quality Intelligence", "", "**Phase:** 5 — Analytical Governance",
             f"**Source:** `{result['source']['filename'].replace('`', '')}`", f"**SHA-256:** `{result['source']['sha256']}`", "",
             "## Data quality gate", "", f"- **Gate:** `{p['quality_gate']}`",
             f"- Input rows: {p['total_rows']}", f"- Usable SKUs: {p['unique_skus']}",
             f"- Next-calendar-day pairs: {p['next_day_pairs']}",
             f"- Phase 5-like candidates: {p['phase5_like_candidate_rows']}",
             f"- Strict three-day windows: {p['strict_three_day_windows']}",
             f"- Duplicate-key rows: {p['duplicate_key_rows']}", f"- Multi-day gaps: {p['multi_day_gaps']}", "",
             "## Attrition", "", "| Stage | Rows |", "| --- | ---: |"]
    lines.extend(f"| {x['stage']} | {x['rows']} |" for x in p["attrition"])
    lines += ["", "## Findings and recommended actions", ""]
    lines.extend(f"- **{x['severity']} / {x['code']}:** {x['detail']} Action: {x['analyst_action']}" for x in p["issues"])
    if not p["issues"]:
        lines.append("- No predefined data issue flagged; no causal claim is implied.")
    comparison = result["baseline_comparison"]
    lines += ["", "## Baseline comparison", ""]
    if comparison:
        lines.extend([f"- Shared SKUs: {comparison['sku_overlap_count']}", f"- Baseline-only SKUs: {comparison['sku_only_baseline_count']}",
                      f"- Current-only SKUs: {comparison['sku_only_current_count']}", "", "| Metric | Baseline | Current | Difference |", "| --- | ---: | ---: | ---: |"])
        lines.extend(f"| {x['metric']} | {x['baseline']} | {x['current']} | {x['absolute_change']} |" for x in comparison["metric_changes"])
        lines += ["", comparison["interpretation_boundary"]]
    else:
        lines.append("- Not supplied.")
    review = result["evidence_review"]
    lines += ["", "## Existing Phase 5 evidence review", ""]
    if review:
        lines.append(f"- Decision-readiness category: `{review['decision_readiness']}`")
        lines.append(f"- Observational effect: `{review['primary_observational_effect']}`")
        lines.extend(f"- **{x['code']}:** {x['finding']}" for x in review["caution_flags"])
    else:
        lines.append("- Not supplied; no model fitted by Week 15.")
    lines += ["", "## Interpretation boundary", "", p["interpretation_boundary"], "",
              "Phase 5-like candidates require a prior observation and next-calendar-day outcome; strict windows additionally require the prior observation to be on the previous calendar day.", "",
              "Duplicate SKU/date keys are excluded in full from temporal calculations. Rates are assumed to be fractions between 0 and 1; review source definitions if rates use another scale.", ""]
    return "\n".join(lines)


def run_week15(unified_csv: Path, output_dir: Path, baseline_csv: Path | None = None,
               phase5_json: Path | None = None) -> dict[str, Any]:
    for path in (unified_csv, baseline_csv, phase5_json):
        if path is not None and not path.is_file():
            raise FileNotFoundError(f"Input file not found: {path}")
    df = pd.read_csv(unified_csv, dtype={"sku_id": "string"})
    profile = analyze_quality(df)
    baseline = analyze_quality(pd.read_csv(baseline_csv, dtype={"sku_id": "string"})) if baseline_csv else None
    comparison = compare_profiles(baseline, profile) if baseline is not None else None
    review = None
    if phase5_json:
        with phase5_json.open(encoding="utf-8") as handle:
            intelligence = json.load(handle)
        review = build_week12_evidence_review(intelligence)
    result: dict[str, Any] = {
        "week": 15, "source": {"filename": unified_csv.name, "sha256": sha256_file(unified_csv)},
        "baseline": {"filename": baseline_csv.name, "sha256": sha256_file(baseline_csv)} if baseline_csv else None,
        "phase5_input": {"filename": phase5_json.name, "sha256": sha256_file(phase5_json)} if phase5_json else None,
        "quality_profile": profile, "baseline_comparison": comparison, "evidence_review": review,
        "outputs": ["week15_quality.json", "week15_quality.md", "week15_quality.html", "week15_sku_coverage.csv"],
        "methodology": "Descriptive quality screening; no causal model fitted or business action authorized.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "week15_quality.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (output_dir / "week15_quality.md").write_text(render_quality_markdown(result), encoding="utf-8")
    (output_dir / "week15_quality.html").write_text(render_quality_html(profile, comparison, review, unified_csv.name, result["source"]["sha256"]), encoding="utf-8")
    sku_export = pd.DataFrame(profile["per_sku"], columns=SKU_COLUMNS)
    # Prevent spreadsheet formula interpretation of untrusted SKU identifiers.
    if not sku_export.empty:
        sku_export["sku_id"] = sku_export["sku_id"].map(
            lambda value: "'" + value if str(value).lstrip().startswith(("=", "+", "-", "@")) else value
        )
    sku_export.to_csv(output_dir / "week15_sku_coverage.csv", index=False)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Week 15 reproducible daily-SKU quality intelligence; does not fit a model.")
    parser.add_argument("--unified-csv", required=True, type=Path)
    parser.add_argument("--baseline-csv", type=Path, help="Optional earlier unified CSV for descriptive comparison")
    parser.add_argument("--phase5-json", type=Path, help="Optional existing Phase 5 JSON response for Week 12 evidence review")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[2] / "reports" / "week15")
    args = parser.parse_args()
    try:
        result = run_week15(args.unified_csv, args.output_dir, args.baseline_csv, args.phase5_json)
    except (OSError, ValueError, TypeError, json.JSONDecodeError, pd.errors.ParserError) as exc:
        parser.error(str(exc))
    print("Week 15 quality gate:", result["quality_profile"]["quality_gate"])
    print("Phase 5-like candidate rows:", result["quality_profile"]["phase5_like_candidate_rows"])
    for name in result["outputs"]:
        print("Report:", (args.output_dir / name).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
