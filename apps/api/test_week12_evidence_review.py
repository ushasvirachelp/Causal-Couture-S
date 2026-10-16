"""Run: python3 -m unittest -v test_week12_evidence_review.py"""
import unittest
from causal_evidence_review import build_week12_evidence_review, render_week12_markdown


class Week12EvidenceReviewTests(unittest.TestCase):
    def base(self):
        return {
            "estimated_effect": 0.2,
            "uncertainty": {"status": "estimated", "confidence_interval_95": {"lower": 0.1, "upper": 0.3}},
            "cluster_uncertainty": {"status": "estimated", "confidence_interval_95": {"lower": 0.05, "upper": 0.35}},
            "placebo_test": {"status": "estimated", "placebo_effect": 0.01},
            "temporal_placebo_test": {"status": "estimated", "temporal_placebo_effect": 0.01},
            "unobserved_confounding_sensitivity": {"status": "estimated", "stress_results": [], "first_direction_change": None},
            "overlap_diagnostic": {"status": "analyzed", "overlap_status": "review"},
            "stockout_diagnostic": {"status": "analyzed", "suppressed_demand_risk": {"level": "LOW"}},
            "robustness_diagnostic": {"status": "estimated"},
            "evidence_summary": {"status": "estimated"},
        }

    def test_fully_reported_is_only_exploratory(self):
        result = build_week12_evidence_review(self.base())
        self.assertEqual(result["decision_readiness"], "exploratory_interpretation_only")

    def test_interval_disagreement_parses_actual_dict_shape(self):
        payload = self.base()
        payload["cluster_uncertainty"]["confidence_interval_95"] = {"lower": -0.1, "upper": 0.35}
        result = build_week12_evidence_review(payload)
        self.assertEqual(result["decision_readiness"], "analyst_review_required")
        self.assertIn("bootstrap_interval_disagreement", [f["code"] for f in result["caution_flags"]])

    def test_missing_diagnostic_is_not_favorable(self):
        payload = self.base()
        del payload["placebo_test"]
        result = build_week12_evidence_review(payload)
        self.assertEqual(result["decision_readiness"], "insufficient_evidence_for_decision")

    def test_diagnostic_error_is_not_favorable(self):
        payload = self.base()
        payload["temporal_placebo_test"] = {"status": "diagnostic_error", "error": "bad data"}
        result = build_week12_evidence_review(payload)
        self.assertEqual(result["diagnostic_counts"]["errors"], 1)

    def test_unrecognized_status_is_not_favorable(self):
        payload = self.base()
        payload["robustness_diagnostic"] = {"status": "new_status"}
        result = build_week12_evidence_review(payload)
        self.assertEqual(result["decision_readiness"], "insufficient_evidence_for_decision")

    def test_sensitivity_flag(self):
        payload = self.base()
        payload["unobserved_confounding_sensitivity"]["first_direction_change"] = "moderate"
        result = build_week12_evidence_review(payload)
        self.assertIn("synthetic_confounding_direction_change", [f["code"] for f in result["caution_flags"]])

    def test_overlap_and_stockout_flags(self):
        payload = self.base()
        payload["overlap_diagnostic"]["overlap_status"] = "poor"
        payload["stockout_diagnostic"]["suppressed_demand_risk"]["level"] = "HIGH"
        result = build_week12_evidence_review(payload)
        self.assertIn("poor_treatment_variation", [f["code"] for f in result["caution_flags"]])
        self.assertIn("inventory_pressure", [f["code"] for f in result["caution_flags"]])

    def test_missing_effect(self):
        payload = self.base()
        payload["estimated_effect"] = None
        result = build_week12_evidence_review(payload)
        self.assertEqual(result["decision_readiness"], "insufficient_evidence_for_decision")

    def test_markdown_output(self):
        report = render_week12_markdown(build_week12_evidence_review(self.base()), "example.csv")
        self.assertIn("Week 12 Evidence Review", report)
        self.assertIn("example.csv", report)
        self.assertIn("SKU-cluster", report)


if __name__ == "__main__":
    unittest.main()
