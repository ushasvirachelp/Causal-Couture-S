# Causal Couture — Week 15 Installation & Execution

**Reporting week:** November 2–8, 2026. **Package created:** November 8, 2026.

This is a **new-file-only** extension to the existing Phase 5 project. It does not replace `main.py`, the existing causal estimator, or the Week 12–14 modules. The CLI **does not fit a causal model**, connect to an external service, or modify your input CSV.

## New files

- `apps/api/causal_quality_gate.py` — data integrity, attrition, temporal coverage, quality guidance, SKU profiles.
- `apps/api/causal_quality_comparison.py` — optional descriptive baseline/current comparison.
- `apps/api/causal_quality_dashboard.py` — standalone offline HTML dashboard.
- `apps/api/run_week15_quality.py` — CLI and JSON/Markdown/HTML/SKU CSV exports.
- `apps/api/test_week15_quality.py` — 20 unit tests.
- `docs/WEEK15_INSTALL_AND_RUN.md` — this guide.
- `docs/WEEK15_TECHNICAL_REPORT.md` — truthful technical reporting draft.

## 1. Install on your Mac

Download `Causal_Couture_Week15_Complete.zip` to Downloads and unzip into the **repository root**:

```bash
cd ~/Desktop/Causal-Couture-Solo
unzip -o ~/Downloads/Causal_Couture_Week15_Complete.zip -d ~/Desktop/Causal-Couture-Solo
```

Confirm the new files appear under `apps/api` and `docs`.

## 2. Run Week 15 tests

```bash
cd ~/Desktop/Causal-Couture-Solo/apps/api
source .venv/bin/activate
python3 -m unittest -v test_week15_quality
```

Expected in the development environment: `Ran 20 tests` followed by `OK`. Your Mac results must be checked separately.

Optional regression tests for the earlier evidence-review packages:

```bash
python3 -m unittest -v test_week12_evidence_review test_week14_validation test_week15_quality
```

This combined suite passed 39 tests in the isolated development environment. It does **not** exercise the complete FastAPI application or production data.

## Optional quick demo (synthetic data only)

The ZIP includes `examples/SYNTHETIC_demo_daily_sku.csv` so you can inspect the dashboard before running on real data:

```bash
python3 run_week15_quality.py \
  --unified-csv ../../examples/SYNTHETIC_demo_daily_sku.csv \
  --output-dir ../../reports/week15_demo
open ../../reports/week15_demo/week15_quality.html
```

These rows are **invented test fixtures**, not observed retail performance. Do not include synthetic metrics in your fellowship results.

## 3. Generate your actual dataset report

The following filename was seen previously in your local repository. Confirm it still exists; otherwise substitute your current unified CSV.

```bash
python3 run_week15_quality.py \
  --unified-csv ../../data/processed/unified/20260923_221605_unified_daily_sku.csv
```

Outputs under `reports/week15/`:

- `week15_quality.json` — machine-readable quality metrics, checks, provenance hash.
- `week15_quality.md` — report with findings and analyst actions.
- `week15_quality.html` — standalone visual dashboard.
- `week15_sku_coverage.csv` — SKU-level temporal coverage, with spreadsheet formula protection.

Open the dashboard:

```bash
open ../../reports/week15/week15_quality.html
```

A `blocked` result is **not a code failure**; it can mean the real dataset lacks enough usable consecutive observations. Review the reported issues instead of manufacturing results.

## 4. Optional baseline comparison

Supply a *different* real unified CSV to compare descriptive quality and SKU coverage. This is **not** a statistical drift test.

```bash
python3 run_week15_quality.py \
  --unified-csv ../../data/processed/unified/CURRENT.csv \
  --baseline-csv ../../data/processed/unified/BASELINE.csv
```

## 5. Optional saved Phase 5 evidence

Use an **existing** JSON response from `/phase5/causal-intelligence`; this will call the existing Week 12 evidence review **without refitting** the model:

```bash
python3 run_week15_quality.py \
  --unified-csv ../../data/processed/unified/CURRENT.csv \
  --phase5-json /absolute/path/to/saved_phase5.json
```

No new causal effect is calculated by Week 15. Do not present quality guidance as proof of causal identification, statistical significance, or business impact.

## 6. Stage and commit after verifying locally

```bash
cd ~/Desktop/Causal-Couture-Solo
git status
git add apps/api/causal_quality_gate.py \
  apps/api/causal_quality_comparison.py \
  apps/api/causal_quality_dashboard.py \
  apps/api/run_week15_quality.py \
  apps/api/test_week15_quality.py \
  docs/WEEK15_INSTALL_AND_RUN.md \
  docs/WEEK15_TECHNICAL_REPORT.md
git diff --cached --stat
git commit -m "Add Week 15 data quality intelligence and governance reporting"
git push origin main
```

**Do not use `git add .`**: it can unintentionally include generated CSVs, reports, credentials, and caches. Report the actual commit hash after pushing. The report is a draft until local execution and GitHub evidence are recorded.

## Notes on interpretation

- `engagement_rate` is assumed to be a fraction in `[0,1]`. If your source stores percentages in `[0,100]`, normalize *upstream* only after confirming its definition.
- Negative `units_sold` is flagged as invalid; if the source uses negative values for returns, handle those separately before running the quality gate.
- All duplicate SKU/date keys are excluded from temporal counts (not silently deduplicated).
- Phase 5-like candidate rows require a previous **observation** and next **calendar day**. Strict three-day windows additionally require the previous observation to be on the previous calendar day. This distinction is deliberate and follows the current `causal_dataset.py` design.
- The quality gate's labels are descriptive guidance, not model validation. Even clean data can suffer confounding, measurement bias, insufficient sample size, or invalid assumptions.
