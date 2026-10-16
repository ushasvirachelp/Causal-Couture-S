"""Run a Week 12 evidence audit from a saved API JSON or a unified CSV.

Examples:
  python run_week12_evidence_review.py --input-json phase5_output.json
  python run_week12_evidence_review.py --unified-csv ../../data/processed/unified/file.csv
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from causal_evidence_review import build_week12_evidence_review, render_week12_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a reproducible Week 12 Phase 5 evidence review.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input-json", type=Path, help="Saved /phase5/causal-intelligence JSON response")
    source.add_argument("--unified-csv", type=Path, help="Unified date-by-SKU CSV; runs the existing Phase 5 pipeline")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[2] / "reports" / "week12")
    args = parser.parse_args()

    if args.input_json:
        path = args.input_json
        if not path.is_file():
            parser.error(f"Input JSON not found: {path}")
        with path.open(encoding="utf-8") as handle:
            intelligence = json.load(handle)
    else:
        path = args.unified_csv
        if not path.is_file():
            parser.error(f"Unified CSV not found: {path}")
        import pandas as pd
        from causal_intelligence import build_causal_intelligence
        intelligence = build_causal_intelligence(pd.read_csv(path))

    review = build_week12_evidence_review(intelligence)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "week12_evidence_review.json"
    md_path = args.output_dir / "week12_evidence_review.md"
    json_path.write_text(json.dumps(review, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    md_path.write_text(render_week12_markdown(review, path.name), encoding="utf-8")
    print(f"Review category: {review['decision_readiness']}")
    print(f"JSON: {json_path.resolve()}")
    print(f"Markdown: {md_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
