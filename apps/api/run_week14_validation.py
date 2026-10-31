from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
from causal_data_readiness import profile_unified_data
from causal_review_dashboard import render_validation_html
from causal_evidence_review import build_week12_evidence_review


def render_validation_markdown(profile: dict | None, review: dict | None, source: str) -> str:
    lines = ["# Causal Couture — Week 14 Validation Report", "", f"**Source:** `{source.replace('`', '')}`", "", "## Data preflight", ""]
    if profile is None:
        lines.append("- Not run (existing Phase 5 JSON supplied).")
    else:
        for key in ("rows", "unique_skus", "date_min", "date_max", "next_calendar_day_pairs", "candidate_causal_rows", "model_run_guidance"):
            lines.append(f"- {key}: `{profile.get(key)}`")
        for item in profile["issues"]:
            lines.append(f"- **{item['severity']} — {item['code']}:** {item['detail']}")
    lines += ["", "## Causal evidence review", ""]
    if review is None:
        lines.append("- Not run. Data profiling alone does not fit a causal model.")
    else:
        lines.append(f"- Decision-readiness category: `{review['decision_readiness']}`")
        lines.append(f"- Primary observational effect: `{review['primary_observational_effect']}`")
        lines += [f"- **{f['code']}:** {f['finding']}" for f in review["caution_flags"]]
    lines += ["", "## Interpretation boundary", "", "Preflight checks and observational diagnostics do not establish causality or authorize automatic business decisions.", ""]
    return "\n".join(lines)


def run_validation(unified_csv: Path | None, input_json: Path | None, output_dir: Path, run_phase5: bool = False) -> dict:
    if (unified_csv is None) == (input_json is None):
        raise ValueError("Supply exactly one of unified_csv or input_json.")
    if run_phase5 and unified_csv is None:
        raise ValueError("--run-phase5 is only valid with --unified-csv.")
    profile = None
    intelligence = None
    source = unified_csv or input_json
    if not source.is_file():
        raise FileNotFoundError(f"Input file not found: {source}")
    if unified_csv is not None:
        df = pd.read_csv(unified_csv)
        profile = profile_unified_data(df)
        if run_phase5:
            if profile["model_run_guidance"] == "blocked":
                raise ValueError("Phase 5 cannot run: missing required columns or empty dataset. Run preflight without --run-phase5 first.")
            from causal_intelligence import build_causal_intelligence
            intelligence = build_causal_intelligence(df)
    else:
        with input_json.open(encoding="utf-8") as f:
            intelligence = json.load(f)
        if not isinstance(intelligence, dict):
            raise ValueError("Expected a JSON object with Phase 5 fields.")
    review = build_week12_evidence_review(intelligence) if intelligence is not None else None
    output_dir.mkdir(parents=True, exist_ok=True)
    result = {"week": 14, "source_filename": source.name, "data_preflight": profile, "evidence_review": review,
              "validation_boundary": "No causal identification or business impact has been validated by this report."}
    (output_dir / "week14_validation.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (output_dir / "week14_validation.md").write_text(render_validation_markdown(profile, review, source.name), encoding="utf-8")
    (output_dir / "week14_validation.html").write_text(render_validation_html(profile, review, source.name), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Week 14 preflight and optional evidence review.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--unified-csv", type=Path)
    source.add_argument("--input-json", type=Path)
    parser.add_argument("--run-phase5", action="store_true", help="Explicitly run the existing full Phase 5 pipeline (may take time).")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[2] / "reports" / "week14")
    args = parser.parse_args()
    try:
        result = run_validation(args.unified_csv, args.input_json, args.output_dir, args.run_phase5)
    except (OSError, ValueError, json.JSONDecodeError, pd.errors.ParserError) as exc:
        parser.error(str(exc))
    print("Preflight:", (result["data_preflight"] or {}).get("model_run_guidance", "not_run"))
    print("Evidence review:", (result["evidence_review"] or {}).get("decision_readiness", "not_run"))
    for extension in ("json", "md", "html"):
        print("Report:", (args.output_dir / f"week14_validation.{extension}").resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())