# Causal Couture — Week 14 Technical Progress Report

**Reporting window:** October 26–November 1, 2026 (week still in progress as of October 31)  
**Phase:** 5 — Causal Intelligence / Evidence Reliability

## Objective

Implement a reproducible preflight for the unified daily-SKU dataset and make the existing Week 12 evidence review easier to inspect through a standalone offline HTML report.

## Implementation prepared October 31

- `apps/api/causal_data_readiness.py`: checks required columns, invalid values, duplicate SKU/date records, usable SKUs, consecutive-day pairs, candidate causal rows, and treatment variation. Does **not** fit a causal model.
- `apps/api/causal_review_dashboard.py`: generates a self-contained, HTML-escaped report with data-readiness metrics, diagnostic status inventory, and caution flags.
- `apps/api/run_week14_validation.py`: CLI that writes JSON, Markdown, and HTML reports. `--unified-csv` profiles data by default. `--run-phase5` explicitly invokes the existing Phase 5 pipeline. `--input-json` reviews an existing saved Phase 5 response without refitting.
- `apps/api/test_week14_validation.py`: unit tests for temporal structure, missing columns, empty inputs, duplicates, invalid values, safe HTML output, and report generation.

## Validation and evidence

On October 31, the package was tested in an isolated development environment against the existing Week 12 module: **10/10 Week 14 unit tests passed**. A synthetic six-row CSV also generated all three report formats successfully. These are development checks, **not** tests run on the user's Mac or validation against actual retail data. Record actual local test results and Git commit after running the commands in `WEEKS13_14_INSTALL_AND_RUN.md`.

**No real-dataset validation or production deployment is claimed.** Test fixtures, if used, are synthetic examples and not empirical retail outcomes. No GitHub commit for these weeks is claimed in this document.

## Outstanding

- Run Week 14 preflight against an actual local unified CSV and inspect the generated reports.
- If the data are sufficient, explicitly run the existing Phase 5 pipeline and review diagnostic limitations.
- Capture a screenshot of the offline report, if useful for the fellowship update.
- Commit the actual files after local verification; record the real commit hash.
