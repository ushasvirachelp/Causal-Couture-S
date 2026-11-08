"""Week 15 tests: python3 -m unittest -v test_week15_quality"""
import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from causal_quality_gate import analyze_quality
from causal_quality_comparison import compare_profiles
from causal_quality_dashboard import render_quality_html
from run_week15_quality import run_week15, sha256_file


class Week15QualityTests(unittest.TestCase):
    def example(self):
        return pd.DataFrame({
            "date": ["2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04"] * 2,
            "sku_id": ["A"] * 4 + ["B"] * 4,
            "units_sold": [3, 4, 5, 6, 7, 8, 9, 10],
            "engagement_rate": [.1, .2, .3, .4, .2, .3, .4, .5],
        })

    def test_clean_three_day_windows(self):
        p = analyze_quality(self.example())
        self.assertEqual(p["quality_gate"], "candidate_for_exploratory_analysis")
        self.assertEqual(p["next_day_pairs"], 6)
        self.assertEqual(p["phase5_like_candidate_rows"], 4)
        self.assertEqual(p["strict_three_day_windows"], 4)

    def test_missing_columns_block(self):
        p = analyze_quality(self.example().drop(columns=["date"]))
        self.assertEqual(p["quality_gate"], "blocked")
        self.assertIn("date", p["missing_columns"])

    def test_empty_dataset_blocks(self):
        p = analyze_quality(self.example().iloc[:0])
        self.assertEqual(p["quality_gate"], "blocked")

    def test_missing_sku_and_date(self):
        df = self.example()
        df.loc[0, "sku_id"] = " "
        df.loc[1, "date"] = "invalid"
        p = analyze_quality(df)
        self.assertEqual(p["invalid_counts"]["sku_id"], 1)
        self.assertEqual(p["invalid_counts"]["date"], 1)

    def test_negative_sales_excluded(self):
        df = self.example()
        df.loc[1, "units_sold"] = -4
        p = analyze_quality(df)
        self.assertEqual(p["invalid_counts"]["negative_units_sold"], 1)
        self.assertEqual(p["quality_gate"], "requires_review")

    def test_invalid_engagement_excluded(self):
        df = self.example()
        df.loc[0, "engagement_rate"] = 1.3
        p = analyze_quality(df)
        self.assertEqual(p["invalid_counts"]["engagement_outside_0_1"], 1)

    def test_duplicate_conflict_excluded(self):
        df = pd.concat([self.example(), self.example().iloc[[0]].assign(units_sold=99)], ignore_index=True)
        p = analyze_quality(df)
        self.assertEqual(p["duplicate_key_rows"], 2)
        self.assertEqual(p["duplicate_conflict_keys"], 1)
        self.assertEqual(p["quality_gate"], "requires_review")
        self.assertEqual(p["attrition"][3]["rows"], 7)

    def test_exact_duplicate_excluded(self):
        df = pd.concat([self.example(), self.example().iloc[[0]]], ignore_index=True)
        p = analyze_quality(df)
        self.assertEqual(p["duplicate_key_rows"], 2)
        self.assertEqual(p["duplicate_conflict_keys"], 0)

    def test_temporal_gaps_strict_vs_phase5(self):
        df = self.example().iloc[:4].copy()
        df.loc[df["date"] == "2026-10-03", "date"] = "2026-10-05"
        df.loc[df["date"] == "2026-10-04", "date"] = "2026-10-06"
        p = analyze_quality(df)
        self.assertEqual(p["multi_day_gaps"], 1)
        self.assertEqual(p["phase5_like_candidate_rows"], 1)
        self.assertEqual(p["strict_three_day_windows"], 0)

    def test_no_candidates_blocks(self):
        df = self.example().iloc[[0, 4]]
        p = analyze_quality(df)
        self.assertEqual(p["quality_gate"], "blocked")

    def test_constant_engagement_warns(self):
        df = self.example()
        df["engagement_rate"] = 0.2
        p = analyze_quality(df)
        self.assertEqual(p["quality_gate"], "requires_review")

    def test_comparison_counts_sku_overlap(self):
        baseline = analyze_quality(self.example())
        df = self.example().copy()
        df.loc[df["sku_id"] == "B", "sku_id"] = "C"
        comp = compare_profiles(baseline, analyze_quality(df))
        self.assertEqual(comp["sku_overlap_count"], 1)
        self.assertEqual(comp["sku_only_baseline_count"], 1)
        self.assertEqual(comp["sku_only_current_count"], 1)

    def test_comparison_rejects_nonprofile(self):
        with self.assertRaises(ValueError):
            compare_profiles({}, {})

    def test_html_escapes_sku_and_filename(self):
        df = self.example()
        df.loc[df["sku_id"] == "A", "sku_id"] = '<script>alert("x")</script>'
        p = analyze_quality(df)
        html = render_quality_html(p, None, None, '<img src=x onerror=alert(1)>', "abc")
        self.assertNotIn('<script>alert("x")</script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('&lt;img', html)

    def test_four_outputs_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv = root / "data.csv"
            self.example().to_csv(csv, index=False)
            result = run_week15(csv, root / "out")
            for name in result["outputs"]:
                self.assertTrue((root / "out" / name).is_file())
            self.assertEqual(result["source"]["sha256"], sha256_file(csv))
            self.assertEqual(len(pd.read_csv(root / "out" / "week15_sku_coverage.csv")), 2)

    def test_baseline_and_saved_phase5(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv = root / "data.csv"
            baseline = root / "baseline.csv"
            phase5 = root / "phase5.json"
            self.example().to_csv(csv, index=False)
            self.example().iloc[:4].to_csv(baseline, index=False)
            phase5.write_text(json.dumps({"estimated_effect": 0.2}), encoding="utf-8")
            result = run_week15(csv, root / "out", baseline, phase5)
            self.assertIsNotNone(result["baseline_comparison"])
            self.assertEqual(result["evidence_review"]["decision_readiness"], "insufficient_evidence_for_decision")

    def test_missing_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                run_week15(Path(tmp) / "missing.csv", Path(tmp) / "out")

    def test_json_and_csv_have_no_nan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv = root / "data.csv"
            df = self.example()
            df["engagement_rate"] = float("nan")
            df.to_csv(csv, index=False)
            run_week15(csv, root / "out")
            json.loads((root / "out" / "week15_quality.json").read_text(), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))

    def test_spreadsheet_formula_sku_is_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv = root / "data.csv"
            df = self.example()
            df.loc[df["sku_id"] == "A", "sku_id"] = "=2+2"
            df.to_csv(csv, index=False)
            run_week15(csv, root / "out")
            exported = (root / "out" / "week15_sku_coverage.csv").read_text()
            self.assertIn("'=2+2", exported)

    def test_no_raw_rows_in_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv = root / "data.csv"
            self.example().to_csv(csv, index=False)
            result = run_week15(csv, root / "out")
            self.assertNotIn("raw_rows", result["quality_profile"])
            self.assertNotIn("records", result["quality_profile"])


if __name__ == "__main__":
    unittest.main()
