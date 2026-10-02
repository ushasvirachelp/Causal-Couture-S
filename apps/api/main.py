from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json
from pathlib import Path
from typing import Any, Optional
from io import BytesIO
from datetime import datetime
from scenario import run_scenario
from trends import build_trend_summary
from dashboard import build_dashboard
from analytics import build_scorecard
from causal_dataset import build_causal_dataset, get_causal_dataset_summary
from causal_estimator import estimate_engagement_effect
from causal_validation import bootstrap_engagement_effect, run_placebo_test
from causal_overlap import analyze_treatment_overlap
from causal_stockout import analyze_stockout_bias, add_inventory_demand_status
from causal_evidence import build_causal_evidence_summary
from causal_robustness import run_robustness_checks
from causal_intelligence import build_causal_intelligence
from causal_cluster_bootstrap import cluster_bootstrap_engagement_effect
from causal_temporal_placebo import run_temporal_placebo_test
from causal_sensitivity import run_unobserved_confounding_sensitivity

app = FastAPI(title="Causal Couture API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parents[2]
SCHEMA_PATH = BASE_DIR / "packages" / "shared" / "schemas.json"
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
UNIFIED_DIR = PROCESSED_DIR / "unified"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
UNIFIED_DIR.mkdir(parents=True, exist_ok=True)

with open(SCHEMA_PATH, "r") as f:
    SCHEMAS = json.load(f)


def validate_dataframe(df: pd.DataFrame, source_type: str) -> dict[str, Any]:
    schema = SCHEMAS.get(source_type)
    if not schema:
        return {"valid": False, "errors": [f"Unknown source type: {source_type}"], "summary": {}}

    errors = []
    warnings = []

    df.columns = [col.strip() for col in df.columns]

    required_columns = schema["required_columns"]
    date_columns = schema["date_columns"]
    numeric_columns = schema["numeric_columns"]

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"Missing required columns: {missing_columns}")

    if "sku_id" in df.columns:
        missing_sku = df["sku_id"].isna().sum() + (df["sku_id"].astype(str).str.strip() == "").sum()
        if missing_sku > 0:
            errors.append(f"{missing_sku} rows have missing sku_id")
    else:
        errors.append("sku_id column is required")

    for col in date_columns:
        if col in df.columns:
            parsed = pd.to_datetime(df[col], errors="coerce")
            bad_dates = parsed.isna().sum()
            if bad_dates > 0:
                errors.append(f"{bad_dates} invalid date values found in '{col}'")

    for col in numeric_columns:
        if col in df.columns:
            coerced = pd.to_numeric(df[col], errors="coerce")
            bad_numeric = coerced.isna().sum()
            if bad_numeric > 0:
                errors.append(f"{bad_numeric} non-numeric values found in '{col}'")

    if df.empty:
        errors.append("Uploaded file is empty")

    if len(df.columns) == 0:
        errors.append("No columns detected in file")

    summary = {
        "rows": int(df.shape[0]),
        "columns": list(df.columns),
        "source_type": source_type
    }

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings, "summary": summary}


def clean_dataframe(df: pd.DataFrame, source_type: str) -> pd.DataFrame:
    df = df.copy()
    df.columns = [col.strip().lower() for col in df.columns]

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    if "sku_id" in df.columns:
        df["sku_id"] = df["sku_id"].astype(str).str.strip().str.upper()

    schema = SCHEMAS[source_type]
    for col in schema["numeric_columns"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["date", "sku_id"]) if {"date", "sku_id"}.issubset(df.columns) else df
    return df


def build_basic_features(df: pd.DataFrame, source_type: str) -> pd.DataFrame:
    df = df.copy()

    if source_type == "sales":
        df = df.sort_values(["sku_id", "date"])
        df["rolling_units_sold_3d"] = (
            df.groupby("sku_id")["units_sold"]
            .transform(lambda s: s.rolling(3, min_periods=1).mean())
        )
        df["sales_spike_flag"] = (df["units_sold"] > df["rolling_units_sold_3d"] * 1.5).astype(int)

    elif source_type == "inventory":
        if {"opening_stock", "closing_stock"}.issubset(df.columns):
            df["sell_through_rate"] = (
                (df["opening_stock"] - df["closing_stock"]) / df["opening_stock"].replace(0, pd.NA)
            )
            df["sell_through_rate"] = df["sell_through_rate"].fillna(0)
            df["low_stock_flag"] = (df["closing_stock"] <= 5).astype(int)

    elif source_type == "social":
        if {"engagement", "impressions"}.issubset(df.columns):
            df["engagement_rate"] = df["engagement"] / df["impressions"].replace(0, pd.NA)
            df["engagement_rate"] = df["engagement_rate"].fillna(0)
            mean_eng = df["engagement"].mean() if len(df) else 0
            df["social_spike_flag"] = (df["engagement"] > mean_eng * 1.5).astype(int) if mean_eng else 0

    elif source_type == "web":
        if {"product_views", "add_to_cart"}.issubset(df.columns):
            df["view_to_cart_rate"] = df["add_to_cart"] / df["product_views"].replace(0, pd.NA)
            df["view_to_cart_rate"] = df["view_to_cart_rate"].fillna(0)

    return df


def simple_causal_stub(source_type: str, df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"message": "No data available for analysis."}

    if source_type == "sales":
        avg_units = float(df["units_sold"].mean()) if "units_sold" in df.columns else 0
        spikes = int(df["sales_spike_flag"].sum()) if "sales_spike_flag" in df.columns else 0
        return {
            "phase_3_status": "starter_scaffold",
            "analysis_type": "demand_pattern_stub",
            "likely_signal": "sales volatility and demand spikes",
            "average_units_sold": avg_units,
            "spike_days": spikes,
            "note": "This is a Phase 3 starter placeholder, not full causal inference yet."
        }

    if source_type == "inventory":
        low_stock_days = int(df["low_stock_flag"].sum()) if "low_stock_flag" in df.columns else 0
        return {
            "phase_3_status": "starter_scaffold",
            "analysis_type": "stock_constraint_stub",
            "likely_signal": "possible inventory pressure",
            "low_stock_days": low_stock_days,
            "note": "This is a Phase 3 starter placeholder, not full stockout suppression modeling yet."
        }

    if source_type == "social":
        spike_days = int(df["social_spike_flag"].sum()) if "social_spike_flag" in df.columns else 0
        return {
            "phase_3_status": "starter_scaffold",
            "analysis_type": "social_signal_stub",
            "likely_signal": "engagement-driven momentum",
            "social_spike_days": spike_days,
            "note": "This is a Phase 3 starter placeholder, not full causal attribution yet."
        }

    if source_type == "web":
        avg_rate = float(df["view_to_cart_rate"].mean()) if "view_to_cart_rate" in df.columns else 0
        return {
            "phase_3_status": "starter_scaffold",
            "analysis_type": "conversion_signal_stub",
            "likely_signal": "web intent strength",
            "average_view_to_cart_rate": avg_rate,
            "note": "This is a Phase 3 starter placeholder, not full causal effect estimation yet."
        }

    if source_type == "unified":
        cols = set(df.columns)
        return {
            "phase_3_status": "starter_scaffold",
            "analysis_type": "multi_signal_unified_stub",
            "likely_signal": "joined business signals available for downstream causal reasoning",
            "has_sales": "units_sold" in cols,
            "has_inventory": "closing_stock" in cols,
            "has_social": "engagement" in cols,
            "has_web": "product_views" in cols,
            "row_count": int(len(df)),
            "note": "This unified dataset is the bridge into later causal modeling."
        }

    return {"message": "No stub analysis available."}


def read_processed_csv(filename: str) -> pd.DataFrame:
    file_path = PROCESSED_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Processed file not found: {filename}")
    return pd.read_csv(file_path)


def build_explanation_from_scorecard(scorecard: dict[str, Any]) -> dict[str, Any]:
    """
    Convert the structured heuristic scorecard into business-facing language.
    """
    dp = scorecard["demand_pressure_score"]
    sr = scorecard["stock_risk_score"]
    em = scorecard["engagement_momentum_score"]
    cs = scorecard["conversion_strength_score"]
    overall = scorecard["overall_signal_score"]

    recommendation = scorecard.get("recommendation", {})
    action = recommendation.get("action", "HOLD")
    priority = recommendation.get("priority", "LOW")
    confidence = recommendation.get("confidence", "MEDIUM")
    reason = recommendation.get(
        "reason",
        "Current signals do not indicate an immediate change."
    )

    if dp >= 70:
        demand_text = "Demand pressure is strong."
    elif dp >= 40:
        demand_text = "Demand pressure is moderate."
    else:
        demand_text = "Demand pressure is limited."

    if sr >= 70:
        stock_text = "Inventory risk is elevated and needs attention."
    elif sr >= 40:
        stock_text = "Inventory risk is moderate and should be monitored."
    else:
        stock_text = "Inventory risk is currently low."

    if em >= 70:
        engagement_text = "Engagement momentum is strong."
    elif em >= 40:
        engagement_text = "Engagement momentum is moderate."
    else:
        engagement_text = "Engagement momentum is currently weak."

    if cs >= 70:
        conversion_text = "Conversion strength is healthy."
    elif cs >= 40:
        conversion_text = "Conversion strength is moderate."
    else:
        conversion_text = "Conversion strength is weak."

    if overall >= 70:
        summary = "Overall, the combined business signal is strong."
    elif overall >= 45:
        summary = "Overall, the combined business signal is mixed but worth monitoring."
    else:
        summary = "Overall, the current combined business signal is weak."

    action_text = (
        f"Recommended action: {action}. Priority: {priority}. "
        f"Confidence: {confidence}. {reason}"
    )

    full_explanation = " ".join([
        summary,
        demand_text,
        stock_text,
        engagement_text,
        conversion_text,
        action_text,
    ])

    return {
        "summary": summary,
        "demand_interpretation": demand_text,
        "stock_interpretation": stock_text,
        "engagement_interpretation": engagement_text,
        "conversion_interpretation": conversion_text,
        "action": action,
        "priority": priority,
        "confidence": confidence,
        "reason": reason,
        "full_explanation": full_explanation,
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/files/processed")
def list_processed_files() -> dict[str, Any]:
    files = sorted([p.name for p in PROCESSED_DIR.glob("*.csv")], reverse=True)
    return {"count": len(files), "files": files}


@app.get("/files/processed/by-source")
def list_processed_files_by_source() -> dict[str, Any]:
    grouped = {"sales": [], "inventory": [], "social": [], "web": [], "other": []}
    for p in sorted(PROCESSED_DIR.glob("*.csv"), reverse=True):
        name = p.name
        matched = False
        for source in ["sales", "inventory", "social", "web"]:
            if f"_{source}_" in name:
                grouped[source].append(name)
                matched = True
                break
        if not matched:
            grouped["other"].append(name)
    return grouped


@app.get("/files/unified")
def list_unified_files() -> dict[str, Any]:
    files = sorted([p.name for p in UNIFIED_DIR.glob("*.csv")], reverse=True)
    return {"count": len(files), "files": files}


@app.get("/phase2/summary")
def phase2_summary(processed_filename: str) -> dict[str, Any]:
    file_path = PROCESSED_DIR / processed_filename
    if not file_path.exists():
        return {"error": f"Processed file not found: {processed_filename}"}

    df = pd.read_csv(file_path)
    return {
        "rows": int(df.shape[0]),
        "columns": list(df.columns),
        "unique_skus": int(df["sku_id"].nunique()) if "sku_id" in df.columns else 0,
        "date_min": str(df["date"].min()) if "date" in df.columns and len(df) else None,
        "date_max": str(df["date"].max()) if "date" in df.columns and len(df) else None,
        "preview_rows": df.head(5).fillna("").to_dict(orient="records")
    }


@app.post("/phase2/build-unified")
def build_unified_dataset(
    sales_file: Optional[str] = Form(None),
    inventory_file: Optional[str] = Form(None),
    social_file: Optional[str] = Form(None),
    web_file: Optional[str] = Form(None)
) -> dict[str, Any]:
    sources = {
        "sales": sales_file,
        "inventory": inventory_file,
        "social": social_file,
        "web": web_file,
    }

    loaded = {}
    for source, filename in sources.items():
        if filename:
            df = read_processed_csv(filename).copy()
            df.columns = [c.strip().lower() for c in df.columns]
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
            if "sku_id" in df.columns:
                df["sku_id"] = df["sku_id"].astype(str).str.strip().str.upper()
            loaded[source] = df

    if not loaded:
        return {"error": "Provide at least one processed file."}

    unified = None
    for source, df in loaded.items():
        if "date" not in df.columns or "sku_id" not in df.columns:
            return {"error": f"{source} file is missing date or sku_id columns."}

        if unified is None:
            unified = df
        else:
            overlapping = [c for c in df.columns if c in unified.columns and c not in ["date", "sku_id"]]
            rename_map = {c: f"{c}_{source}" for c in overlapping}
            df = df.rename(columns=rename_map)
            unified = unified.merge(df, on=["date", "sku_id"], how="outer")

    unified = unified.sort_values(["date", "sku_id"]).reset_index(drop=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unified_filename = f"{timestamp}_unified_daily_sku.csv"
    unified_path = UNIFIED_DIR / unified_filename
    unified.to_csv(unified_path, index=False)

    return {
        "status": "success",
        "unified_filename": unified_filename,
        "saved_unified_file": str(unified_path),
        "rows": int(unified.shape[0]),
        "columns": list(unified.columns),
        "preview_rows": unified.head(5).fillna("").to_dict(orient="records")
    }


@app.get("/phase3/scorecard")
def phase3_scorecard(processed_filename: str) -> dict[str, Any]:
    file_path = UNIFIED_DIR / processed_filename
    if not file_path.exists():
        return {"error": f"Unified file not found: {processed_filename}"}

    df = pd.read_csv(file_path)
    return build_scorecard(df)


@app.get("/phase3/explain")
def phase3_explain(processed_filename: str) -> dict[str, Any]:
    file_path = UNIFIED_DIR / processed_filename
    if not file_path.exists():
        return {"error": f"Unified file not found: {processed_filename}"}

    df = pd.read_csv(file_path)
    scorecard = build_scorecard(df)
    explanation = build_explanation_from_scorecard(scorecard)

    return {
        "scorecard": scorecard,
        "explanation": explanation
    }


@app.get("/phase3/analyze")
def phase3_analyze(source_type: str, processed_filename: str) -> dict[str, Any]:
    if source_type == "unified":
        file_path = UNIFIED_DIR / processed_filename
    else:
        file_path = PROCESSED_DIR / processed_filename

    if not file_path.exists():
        return {"error": f"Processed file not found: {processed_filename}"}

    df = pd.read_csv(file_path)
    return simple_causal_stub(source_type, df)


@app.post("/phase4/scenario")
def phase4_scenario(
    processed_filename: str = Form(...),
    demand_change_pct: float = Form(0),
    inventory_change_pct: float = Form(0),
    engagement_change_pct: float = Form(0),
    conversion_change_pct: float = Form(0),
) -> dict[str, Any]:
    file_path = UNIFIED_DIR / processed_filename

    if not file_path.exists():
        return {
            "error": f"Unified file not found: {processed_filename}"
        }

    try:
        df = pd.read_csv(file_path)

        result = run_scenario(
            df=df,
            demand_change_pct=demand_change_pct,
            inventory_change_pct=inventory_change_pct,
            engagement_change_pct=engagement_change_pct,
            conversion_change_pct=conversion_change_pct,
        )

        result["processed_filename"] = processed_filename

        return result

    except ValueError as e:
        return {
            "error": str(e)
        }

    except Exception as e:
        return {
            "error": f"Scenario analysis failed: {str(e)}"
        }


@app.post("/upload")
async def upload_file(
    source_type: str = Form(...),
    file: UploadFile = File(...)
) -> dict[str, Any]:
    if not file.filename.lower().endswith(".csv"):
        return {
            "valid": False,
            "errors": ["Only CSV files are supported in Phase 1/2 starter"],
            "summary": {}
        }

    try:
        contents = await file.read()
        df = pd.read_csv(BytesIO(contents))

        validation = validate_dataframe(df, source_type)
        if not validation["valid"]:
            validation["filename"] = file.filename
            return validation

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_filename = f"{timestamp}_{source_type}_{file.filename}"
        raw_path = RAW_DIR / raw_filename

        with open(raw_path, "wb") as f:
            f.write(contents)

        cleaned_df = clean_dataframe(df, source_type)
        featured_df = build_basic_features(cleaned_df, source_type)

        processed_filename = f"{timestamp}_{source_type}_processed.csv"
        processed_path = PROCESSED_DIR / processed_filename
        featured_df.to_csv(processed_path, index=False)

        return {
            "valid": True,
            "errors": [],
            "warnings": [],
            "filename": file.filename,
            "summary": validation["summary"],
            "saved_raw_file": str(raw_path),
            "saved_processed_file": str(processed_path),
            "processed_filename": processed_filename,
            "preview_rows": featured_df.head(5).fillna("").to_dict(orient="records")
        }

    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Failed to process file: {str(e)}"],
            "summary": {}
        }

@app.get("/phase4/trends")
def phase4_trends(
    processed_filename: str,
) -> dict[str, Any]:

    file_path = UNIFIED_DIR / processed_filename

    if not file_path.exists():
        return {
            "error": f"Unified file not found: {processed_filename}"
        }

    try:
        df = pd.read_csv(file_path)

        result = build_trend_summary(df)

        result["processed_filename"] = processed_filename

        return result

    except ValueError as e:
        return {
            "error": str(e)
        }

    except Exception as e:
        return {
            "error": f"Trend analysis failed: {str(e)}"
        }
@app.get("/phase4/dashboard")
def phase4_dashboard(
    processed_filename: str,
) -> dict[str, Any]:

    file_path = UNIFIED_DIR / processed_filename

    if not file_path.exists():
        return {
            "error": f"Unified file not found: {processed_filename}"
        }

    try:
        df = pd.read_csv(file_path)

        result = build_dashboard(df)

        result["processed_filename"] = processed_filename

        return result

    except ValueError as e:
        return {
            "error": str(e)
        }

    except Exception as e:
        return {
            "error": f"Dashboard generation failed: {str(e)}"
        }
@app.post("/phase4/intelligence")
def phase4_intelligence(
    processed_filename: str = Form(...),
    demand_change_pct: float = Form(0),
    inventory_change_pct: float = Form(0),
    engagement_change_pct: float = Form(0),
    conversion_change_pct: float = Form(0),
) -> dict[str, Any]:
    file_path = UNIFIED_DIR / processed_filename

    if not file_path.exists():
        return {
            "error": f"Unified file not found: {processed_filename}"
        }

    try:
        df = pd.read_csv(file_path)

        dashboard_result = build_dashboard(df)

        scenario_result = run_scenario(
            df=df,
            demand_change_pct=demand_change_pct,
            inventory_change_pct=inventory_change_pct,
            engagement_change_pct=engagement_change_pct,
            conversion_change_pct=conversion_change_pct,
        )

        return {
            "processed_filename": processed_filename,
            "dashboard": dashboard_result,
            "scenario": scenario_result,
            "methodology_note": (
                "Dashboard metrics are heuristic/descriptive signals. "
                "Scenario outputs are structured simulations, not causal estimates."
            ),
        }

    except ValueError as e:
        return {
            "error": str(e)
        }

    except Exception as e:
        return {
            "error": f"Intelligence generation failed: {str(e)}"
        }
@app.get("/phase5/causal-dataset")
def phase5_causal_dataset(filename: str):
    """
    Build and inspect the Phase 5 causal-analysis dataset
    from an existing unified dataset.
    """

    try:
        file_path = UNIFIED_DIR / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Unified file not found: {filename}")

        df = pd.read_csv(file_path)

        causal_df = build_causal_dataset(df)
        causal_df = add_inventory_demand_status(causal_df)
        summary = get_causal_dataset_summary(causal_df)

        preview_columns = [
            column
            for column in [
                "date",
                "sku_id",
                "engagement_rate_t",
                "engagement_rate_lag1",
                "units_sold_t",
                "units_sold_lag1",
                "units_sold_next_day",
                "next_observed_date",
                "days_to_next_observation",
                "closing_stock_t",
                "product_views_t",
                "view_to_cart_rate_t",
                "inventory_constrained_flag",
                "demand_observation_status",
                "causal_row_valid",
            ]
            if column in causal_df.columns
        ]

        preview = (
            causal_df[preview_columns]
            .head(25)
            .copy()
        )

        if "date" in preview.columns:
            preview["date"] = preview["date"].astype(str)

        return {
            "phase": "Phase 5",
            "analysis_type": "causal_dataset_preparation",
            "causal_question": (
                "What is the causal effect of social engagement "
                "on subsequent product sales?"
            ),
            "treatment": "engagement_rate_t",
            "outcome": "units_sold_next_day",
            "summary": summary,
            "preview": preview.to_dict(orient="records"),
            "methodology_note": (
                "This endpoint prepares temporal variables for causal analysis. "
                "It does not estimate a causal effect."
            ),
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build causal dataset: {str(exc)}",
        )
@app.get("/phase5/causal-effect")
def phase5_causal_effect(filename: str):
    """
    Estimate the first Phase 5 engagement -> subsequent sales effect
    from an existing unified dataset.
    """

    try:
        file_path = UNIFIED_DIR / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Unified file not found: {filename}")

        df = pd.read_csv(file_path)

        causal_df = build_causal_dataset(df)
        causal_df = add_inventory_demand_status(causal_df)

        estimate = estimate_engagement_effect(causal_df)

        return {
            "phase": "Phase 5",
            "analysis_type": "causal_effect_estimation",
            "causal_question": (
                "What is the causal effect of social engagement "
                "on subsequent product sales?"
            ),
            "treatment": "engagement_rate_t",
            "outcome": "units_sold_next_day",
            "estimate": estimate,
            "methodology_note": (
                "This endpoint uses an adjusted observational linear model. "
                "The result depends on the assumed DAG, available confounders, "
                "temporal ordering, and inventory constraints."
            ),
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to estimate causal effect: {str(exc)}",
        )

@app.get("/phase5/causal-validation")
def phase5_causal_validation(filename: str):
    """
    Run the Phase 5 engagement-effect estimate with uncertainty,
    placebo testing, and treatment-overlap diagnostics.
    """

    try:
        file_path = UNIFIED_DIR / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Unified file not found: {filename}")

        df = pd.read_csv(file_path)
        causal_df = build_causal_dataset(df)
        causal_df = add_inventory_demand_status(causal_df)

        estimate = estimate_engagement_effect(causal_df)

        bootstrap = bootstrap_engagement_effect(
            causal_df,
            estimate_engagement_effect,
        )

        cluster_bootstrap = cluster_bootstrap_engagement_effect(
            causal_df,
            estimate_engagement_effect,
        )

        placebo = run_placebo_test(causal_df)
        temporal_placebo = run_temporal_placebo_test(causal_df)
        sensitivity = run_unobserved_confounding_sensitivity(
            causal_df,
            estimate_engagement_effect,
        )
        overlap = analyze_treatment_overlap(causal_df)
        stockout = analyze_stockout_bias(causal_df)
        robustness = run_robustness_checks(causal_df)

        evidence = build_causal_evidence_summary(
            estimate=estimate,
            uncertainty=bootstrap,
            placebo=placebo,
            overlap=overlap,
            stockout=stockout,
        )

        return {
            "phase": "Phase 5",
            "analysis_type": "causal_effect_validation",
            "causal_question": (
                "What is the causal effect of social engagement "
                "on subsequent product sales?"
            ),
            "treatment": "engagement_rate_t",
            "outcome": "units_sold_next_day",
            "estimate": estimate,
            "uncertainty": bootstrap,
            "cluster_uncertainty": cluster_bootstrap,
            "placebo_test": placebo,
            "temporal_placebo_test": temporal_placebo,
            "unobserved_confounding_sensitivity": sensitivity,
            "overlap_diagnostic": overlap,
            "stockout_diagnostic": stockout,
            "robustness_diagnostic": robustness,
            "evidence_summary": evidence,
            "interpretation_guide": {
                "estimate": (
                    "The adjusted engagement coefficient from the "
                    "observational model."
                ),
                "confidence_interval": (
                    "The row-level bootstrap interval describes uncertainty "
                    "around the estimated coefficient."
                ),
                "cluster_confidence_interval": (
                    "The SKU-level cluster bootstrap resamples entire products "
                    "to better preserve dependence among repeated observations "
                    "of the same SKU."
                ),
                "placebo": (
                    "The shuffled-treatment estimate should ideally "
                    "be much weaker than the original estimate."
                ),
                "temporal_placebo": (
                    "Tests the deliberately impossible direction of future "
                    "next-day engagement predicting current sales. A large "
                    "coefficient is a warning signal for residual temporal "
                    "structure or model misspecification, not causal evidence."
                ),
                "overlap": (
                    "Checks whether engagement has enough observed "
                    "variation to support meaningful treatment comparisons."
                ),
                "stockout": (
                    "Checks whether low or zero inventory may suppress "
                    "observed sales and distort demand measurement."
                ),
                "robustness": (
                    "Compares the engagement effect across alternative model "
                    "specifications to identify specification sensitivity."
                ),
                "evidence_summary": (
                    "Combines the estimate and diagnostics into a transparent "
                    "observational-evidence summary. The evidence score is not "
                    "a probability that the effect is causal."
                ),
            },
            "methodology_note": (
                "These diagnostics improve transparency around row-level and "
                "SKU-cluster uncertainty, shuffled-placebo behavior, temporal falsification, "
                "treatment variation, inventory constraints, and "
                "model-specification stability, but they do not by themselves "
                "establish causal identification."
            ),
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate causal estimate: {str(exc)}",
        )

@app.get("/phase5/causal-intelligence")
def phase5_causal_intelligence(filename: str):
    """
    Build the complete Phase 5 causal-intelligence response
    from an existing unified date × SKU dataset.
    """

    try:
        file_path = UNIFIED_DIR / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Unified file not found: {filename}")

        df = pd.read_csv(file_path)

        result = build_causal_intelligence(df)
        result["filename"] = filename

        return result

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build causal intelligence: {str(exc)}",
        )

