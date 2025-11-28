# mcp_package/server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
import pandas as pd
import os
import json

# Import functions from your parser implementation
# parser.py must define: predict_column_type(values, countries_list, legal_list),
# parse_phone(value, countries_list), parse_company(value, legal_list)
from . import parser as parser_module

app = FastAPI(title="MCP Connector (Claude) - Tools: predict, parse, list_files")

# configuration: where to look for CSVs (project root by default)
PACKAGE_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = PACKAGE_DIR.parent.resolve()  # one level up
RESOURCE_DIR = PACKAGE_DIR  # countries.txt, legal.txt stored here

# Load resource lists once
def load_countries():
    p = RESOURCE_DIR / "countries.txt"
    if not p.exists():
        return []
    return [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]

def load_legal():
    p = RESOURCE_DIR / "legal.txt"
    if not p.exists():
        return []
    return [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]

COUNTRIES = load_countries()
LEGAL = load_legal()


# ---------- Request models ----------
class PredictRequest(BaseModel):
    file: str
    column: Optional[str] = None   # if None, return predictions for all columns


class ParseRequest(BaseModel):
    file: str
    output_path: Optional[str] = "output.csv"  # saved in current working dir by default


# ---------- Helper utilities ----------
def resolve_file(path_str: str) -> Path:
    p = Path(path_str)
    if not p.is_absolute():
        # Look relative to project root, then package dir
        candidates = [PROJECT_ROOT / path_str, PACKAGE_DIR / path_str, Path.cwd() / path_str]
        for c in candidates:
            if c.exists():
                return c.resolve()
        # if still not found, try bare filename in project root
        raise FileNotFoundError(f"File not found: {path_str} (searched project root, package dir, cwd)")
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path_str}")
    return p.resolve()


# ---------- Tool: list available tools ----------
@app.get("/tools")
def list_tools():
    return {
        "tools": [
            {"id": "list_files", "description": "List CSV files available for processing"},
            {"id": "predict", "description": "Predict semantic types for columns or a specific column"},
            {"id": "parse", "description": "Run parsing pipeline (Phone & Company) and write output.csv"},
        ]
    }


# ---------- Tool: list files ----------
@app.get("/files")
def list_files(folder: Optional[str] = None):
    search_dir = PROJECT_ROOT if folder is None else (Path(folder) if Path(folder).exists() else PROJECT_ROOT)
    files = []
    for p in search_dir.glob("**/*"):
        if p.suffix.lower() in {".csv", ".tsv"}:
            files.append(str(p.resolve()))
    # deduplicate and sort
    files = sorted(list(dict.fromkeys(files)))
    return {"files": files, "searched_folder": str(search_dir.resolve())}


# ---------- Tool: predict ----------
@app.post("/predict")
def predict(body: PredictRequest):
    try:
        file_path = resolve_file(body.file)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        # auto-detect delimiter via pandas
        df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read CSV: {e}")

    results: Dict[str, Any] = {}

    if body.column:
        if body.column not in df.columns:
            raise HTTPException(status_code=400, detail=f"Column '{body.column}' not found in file")
        values = df[body.column].tolist()
        label_scores = parser_module.predict_column_type(values, COUNTRIES, LEGAL)
        # parser_module.predict_column_type may return just label (older version) or (label, scores)
        if isinstance(label_scores, tuple) and len(label_scores) == 2:
            label, scores = label_scores
        else:
            label = label_scores
            # compute per-column scores by reusing same function but exposing internals not available -> best effort
            scores = "n/a"
        results = {"column": body.column, "prediction": label, "scores": scores}
    else:
        # run classification for all columns
        col_map = {}
        for col in df.columns:
            values = df[col].tolist()
            label_scores = parser_module.predict_column_type(values, COUNTRIES, LEGAL)
            if isinstance(label_scores, tuple) and len(label_scores) == 2:
                label, scores = label_scores
            else:
                label = label_scores
                scores = "n/a"
            col_map[col] = {"prediction": label, "scores": scores}
        results = {"columns": col_map}

    return {"status": "ok", "file": str(file_path), "result": results}


# ---------- Tool: parse ----------
@app.post("/parse")
def parse(body: ParseRequest):
    try:
        file_path = resolve_file(body.file)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read CSV: {e}")

    # classify each column using parser_module.predict_column_type
    phone_candidates = []
    company_candidates = []
    for col in df.columns:
        res = parser_module.predict_column_type(df[col].tolist(), COUNTRIES, LEGAL)
        if isinstance(res, tuple) and len(res) == 2:
            label, scores = res
        else:
            label = res
            scores = None

        if label == "PhoneNumber":
            # extract phone score if available
            score = scores["PhoneNumber"] if isinstance(scores, dict) and "PhoneNumber" in scores else 1
            phone_candidates.append((col, score))
        if label == "CompanyName":
            score = scores["CompanyName"] if isinstance(scores, dict) and "CompanyName" in scores else 1
            company_candidates.append((col, score))

    # pick best
    phone_col = max(phone_candidates, key=lambda x: x[1])[0] if phone_candidates else None
    company_col = max(company_candidates, key=lambda x: x[1])[0] if company_candidates else None

    out_df = df.copy()

    parse_log = {"phone_col": phone_col, "company_col": company_col}

    if phone_col:
        out_df["Country"] = out_df[phone_col].apply(lambda x: parser_module.parse_phone(str(x), COUNTRIES)[0] if x is not None else None)
        out_df["Number"] = out_df[phone_col].apply(lambda x: parser_module.parse_phone(str(x), COUNTRIES)[1] if x is not None else None)

    if company_col:
        out_df["Name"] = out_df[company_col].apply(lambda x: parser_module.parse_company(str(x), LEGAL)[0] if x is not None else None)
        out_df["Legal"] = out_df[company_col].apply(lambda x: parser_module.parse_company(str(x), LEGAL)[1] if x is not None else None)

    # save output CSV to specified location (relative paths allowed)
    out_path = Path(body.output_path)
    if not out_path.is_absolute():
        out_path = Path.cwd() / out_path
    try:
        out_df.to_csv(out_path, index=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write output: {e}")

    # return small preview for quick check (first 10 rows)
    preview = out_df.head(10).fillna("").to_dict(orient="records")

    return {
        "status": "ok",
        "parsed_file": str(out_path.resolve()),
        "parse_log": parse_log,
        "preview_count": len(preview),
        "preview": preview
    }


# ---------- Health ----------
@app.get("/health")
def health():
    return {"status": "ok", "package_dir": str(PACKAGE_DIR), "project_root": str(PROJECT_ROOT)}
