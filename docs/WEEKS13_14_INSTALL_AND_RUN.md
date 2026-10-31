# Causal Couture — Weeks 13–14 Installation and Run Guide

These are **new files only**. Do not overwrite `main.py`, the Week 12 module, or the website.

## 1. Install

Unzip the package at the root of `~/Desktop/Causal-Couture-Solo`:

```bash
cd ~/Desktop/Causal-Couture-Solo
unzip -o ~/Downloads/Causal_Couture_Weeks13_14_Package.zip -d ~/Desktop/Causal-Couture-Solo
```

## 2. Run Week 14 tests

```bash
cd ~/Desktop/Causal-Couture-Solo/apps/api
source .venv/bin/activate
python3 -m unittest -v test_week14_validation
```

Requires `pandas` and the existing `causal_evidence_review.py` from Week 12.

## 3. Profile your actual dataset (no causal estimation)

```bash
python3 run_week14_validation.py --unified-csv ../../data/processed/unified/20260923_221605_unified_daily_sku.csv
```

The filename above comes from the user's October 16 terminal listing. If the file has moved, replace it with a real local CSV path. No model is fitted by this command.

Generated locally under `reports/week14/`:
- `week14_validation.json`
- `week14_validation.md`
- `week14_validation.html` (open in your browser for screenshots)

Mac:

```bash
open ../../reports/week14/week14_validation.html
```

## 4. Optional: run full existing Phase 5 analysis

Only after inspecting preflight output:

```bash
python3 run_week14_validation.py --unified-csv ../../data/processed/unified/20260923_221605_unified_daily_sku.csv --run-phase5
```

This runs the existing estimator and bootstrap diagnostics and may be slow or fail on sparse data. A preflight warning is not automatically a model failure, and a successful run does not prove causality.

Alternatively, if you have a saved Phase 5 API JSON response:

```bash
python3 run_week14_validation.py --input-json /absolute/path/to/phase5_output.json
```

## 5. Git (after you verify locally)

```bash
cd ~/Desktop/Causal-Couture-Solo
git add docs/WEEK13_DATA_READINESS_PLAN.md docs/WEEK14_PROGRESS_REPORT.md docs/WEEKS13_14_INSTALL_AND_RUN.md \
  apps/api/causal_data_readiness.py apps/api/causal_review_dashboard.py \
  apps/api/run_week14_validation.py apps/api/test_week14_validation.py
git diff --cached --stat
git commit -m "Add Week 13 readiness plan and Week 14 validation reporting"
git push origin main
```

Do **not** `git add .`: generated CSVs, reports, and Python caches may be present. GitHub updates only after **you** run and successfully complete the commands. Record the real commit hash and actual test output in your progress report.