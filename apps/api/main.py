from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json
from pathlib import Path
from typing import Any

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

with open(SCHEMA_PATH, "r") as f:
    SCHEMAS = json.load(f)


def validate_dataframe(df: pd.DataFrame, source_type: str) -> dict[str, Any]:
    schema = SCHEMAS.get(source_type)
    if not schema:
        return {
            "valid": False,
            "errors": [f"Unknown source type: {source_type}"],
            "summary": {}
        }

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

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "summary": summary
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/upload")
async def upload_file(
    source_type: str = Form(...),
    file: UploadFile = File(...)
) -> dict[str, Any]:
    if not file.filename.lower().endswith(".csv"):
        return {
            "valid": False,
            "errors": ["Only CSV files are supported in Phase 1"],
            "summary": {}
        }

    try:
        contents = await file.read()
        from io import BytesIO
        df = pd.read_csv(BytesIO(contents))
        result = validate_dataframe(df, source_type)
        result["filename"] = file.filename
        return result
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Failed to process file: {str(e)}"],
            "summary": {}
        }

