import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from causal_data_readiness import profile_unified_data
from causal_review_dashboard import render_validation_html
from run_week14_validation import run_validation


class Week14ValidationTests(unittest.TestCase):
    def example(self):
        return pd.DataFrame({
            "date": ["2026-10-01", "2026-10-02", "2026-10-03", "2026-10-01", "2026-10-02", "2026-10-03"],
            "sku_id": ["A", "A", "A", "B", "B", "B"],
            "units_sold": [3, 4, 5, 6, 7, 8],
            "engagement_rate": [0.1, 0.2, 0.3, 0.2, 0.3, 0.4],
        })

    def test_consecutive_day_candidates(self):
        p = profile_unified_data(self.example())
        self.assertEqual(p["candidate_causal_rows"], 2)
        self.assertEqual(p["next_calendar_day_pairs"], 4)
        self.assertEqual(p["model_run_guidance"], "candidate_for_exploratory_run")

    def test_missing_column_blocks(self):
        p = profile_unified_data(self.example().drop(columns=["engagement_rate"]))
        self.assertEqual(p["model_run_guidance"], "blocked")
        self.assertIn("engagement_rate", p["required_columns_missing"])

    def test_empty_data_blocks(self):
        p = profile_unified_data(self.example().iloc[:0])
        self.assertEqual(p["model_run_guidance"], "blocked")

    def test_nonconsecutive_dates_not_counted(self):
        df = self.example()
        df.loc[df.date == "2026-10-02", "date"] = "2026-10-07"
        p = profile_unified_data(df)
        self.assertEqual(p["candidate_causal_rows"], 0)

    def test_duplicate_dates_flagged(self):
        df = pd.concat([self.example(), self.example().iloc[:1]], ignore_index=True)
        p = profile_unified_data(df)
        self.assertGreater(p["duplicate_sku_dates"], 0)
        self.assertEqual(p["model_run_guidance"], "requires_review")

    def test_missing_numeric_values_flagged(self):
        df = self.example()
        df["units_sold"] = df["units_sold"].astype(object)
        df.loc[0, "units_sold"] = "bad"
        p = profile_unified_data(df)
        self.assertEqual(p["invalid_or_missing"]["units_sold"], 1)

    def test_html_escapes_source(self):
        html = render_validation_html(None, None, '<script>alert("x")</script>')
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn('<script>alert("x")</script>', html)

    def test_csv_profile_only_creates_three_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv = root / "input.csv"
            self.example().to_csv(csv, index=False)
            result = run_validation(csv, None, root / "out")
            self.assertIsNone(result["evidence_review"])
            self.assertEqual(result["data_preflight"]["candidate_causal_rows"], 2)
            for ext in ("json", "md", "html"):
                self.assertTrue((root / "out" / f"week14_validation.{ext}").exists())

    def test_saved_json_evidence_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "phase5.json"
            path.write_text(json.dumps({"estimated_effect": 0.2}), encoding="utf-8")
            result = run_validation(None, path, root / "out")
            self.assertEqual(result["evidence_review"]["decision_readiness"], "insufficient_evidence_for_decision")
            self.assertIsNone(result["data_preflight"])

    def test_phase5_requires_csv(self):
        with self.assertRaises(ValueError):
            run_validation(None, Path("x.json"), Path("unused"), True)


if __name__ == "__main__":
    unittest.main()