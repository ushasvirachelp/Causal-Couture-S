from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json
from pathlib import Path
from typing import Any, Optional
from io import BytesIO
from datetime import datetime

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


def clamp_score(value: float) -> float:
    return max(0.0, min(100.0, round(value, 2)))


def unified_scorecard(df: pd.DataFrame) -> dict[str, Any]:
    demand_pressure = 0.0
    stock_risk = 0.0
    engagement_momentum = 0.0
    conversion_strength = 0.0

    if "units_sold" in df.columns:
        avg_units = pd.to_numeric(df["units_sold"], errors="coerce").fillna(0).mean()
        demand_pressure = clamp_score(avg_units * 10)

    if "closing_stock" in df.columns:
        avg_stock = pd.to_numeric(df["closing_stock"], errors="coerce").fillna(0).mean()
        stock_risk = clamp_score(100 - (avg_stock * 8))

    if "engagement_rate" in df.columns:
        avg_eng = pd.to_numeric(df["engagement_rate"], errors="coerce").fillna(0).mean()
        engagement_momentum = clamp_score(avg_eng * 10000)

    elif "engagement" in df.columns:
        avg_eng_raw = pd.to_numeric(df["engagement"], errors="coerce").fillna(0).mean()
        engagement_momentum = clamp_score(avg_eng_raw / 2)

    if "view_to_cart_rate" in df.columns:
        avg_conv = pd.to_numeric(df["view_to_cart_rate"], errors="coerce").fillna(0).mean()
        conversion_strength = clamp_score(avg_conv * 1000)

    elif {"add_to_cart", "product_views"}.issubset(df.columns):
        views = pd.to_numeric(df["product_views"], errors="coerce").fillna(0).sum()
        carts = pd.to_numeric(df["add_to_cart"], errors="coerce").fillna(0).sum()
        conversion_strength = clamp_score((carts / views) * 1000) if views > 0 else 0

    overall_signal = clamp_score(
        (0.35 * demand_pressure) +
        (0.25 * (100 - stock_risk)) +
        (0.20 * engagement_momentum) +
        (0.20 * conversion_strength)
    )

    if overall_signal >= 70:
        recommendation = "High momentum — monitor closely and consider inventory prioritization."
    elif overall_signal >= 45:
        recommendation = "Moderate signal — continue tracking and validate across more days."
    else:
        recommendation = "Weak signal — avoid overcommitting inventory until stronger evidence appears."

    return {
        "phase_3_status": "starter_scaffold_plus_scorecard",
        "analysis_type": "unified_signal_scorecard",
        "demand_pressure_score": demand_pressure,
        "stock_risk_score": stock_risk,
        "engagement_momentum_score": engagement_momentum,
        "conversion_strength_score": conversion_strength,
        "overall_signal_score": overall_signal,
        "recommendation": recommendation,
        "note": "These are heuristic starter scores to support early-stage decision reasoning before full causal effect modeling."
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
    return unified_scorecard(df)


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
