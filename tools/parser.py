
import pandas as pd
import argparse
import re
import os

# --------------------------
# Helper Functions
# --------------------------

def is_phone(value):
    if not isinstance(value, str):
        return False
    value = value.strip()
    phone_pattern = r'^\+?\d[\d\s\-\(\)]{5,}$'
    return bool(re.match(phone_pattern, value))

def is_country(value, country_set):
    if not isinstance(value, str):
        return False
    return value.lower().strip() in country_set

def is_date(value):
    if not isinstance(value, str):
        return False
    patterns = [
        r'^\d{2}[-/\.]\d{2}[-/\.]\d{4}$',
        r'^\d{4}[-/\.]\d{2}[-/\.]\d{2}$',
        r'^\d{8}$',
        r'^\d{1,2}[-/\.]\w{3}[-/\.]\d{4}$'
    ]
    for p in patterns:
        if re.match(p, value.strip()):
            return True
    return False

def is_company(value, legal_set):
    if not isinstance(value, str):
        return False
    lower_val = value.lower()
    for ls in legal_set:
        if ls and ls in lower_val:
            return True
    return False

def predict_column_type(values, countries_list, legal_list):
    sample = [str(v) for v in values[:200] if str(v).strip() != ""]

    country_set = set([c.lower().strip() for c in countries_list])
    legal_set = set([l.lower().strip() for l in legal_list])

    scores = {
        "PhoneNumber": sum(is_phone(v) for v in sample),
        "Country": sum(is_country(v, country_set) for v in sample),
        "Date": sum(is_date(v) for v in sample),
        "CompanyName": sum(is_company(v, legal_set) for v in sample),
        "Other": 0
    }

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "Other", scores
    return best, scores


# --------------------------
# Parsing functions
# --------------------------

def parse_phone(value, countries_list):
    if not isinstance(value, str):
        return None, None

    v = value.strip()
    
    match = re.match(r'^(\+\d{1,3})[\s-]?(.*)$', v)
    if match:
        code = match.group(1)
        number = match.group(2).replace(" ", "").replace("-", "")
    else:
        return None, v.replace(" ", "").replace("-", "")

    code_map = {
        "+1": "US",
        "+44": "UK",
        "+91": "India"
    }

    country_name = code_map.get(code, code)
    return country_name, number


def parse_company(value, legal_list):
    if not isinstance(value, str):
        return value, ""

    lower = value.lower().strip()

    for ls in sorted(legal_list, key=lambda x: -len(x)):
        if ls and ls in lower:
            name = lower.replace(ls, "").strip()
            return name, ls

    return value, ""


# --------------------------
# Main Program
# --------------------------

parser = argparse.ArgumentParser()
parser.add_argument("--input", type=str, required=True)
args = parser.parse_args()

df = pd.read_csv(args.input)

# FIXED RESOURCE PATH
resource_folder = "/kaggle/input/our-dataset"

countries_list = open(os.path.join(resource_folder, "countries.txt")).read().strip().split("\n")
legal_list = open(os.path.join(resource_folder, "legal.txt")).read().strip().split("\n")

phone_candidates = []
company_candidates = []

# classify all columns
for col in df.columns:
    col_type, scores = predict_column_type(df[col].tolist(), countries_list, legal_list)
    if col_type == "PhoneNumber":
        phone_candidates.append((col, scores["PhoneNumber"]))
    elif col_type == "CompanyName":
        company_candidates.append((col, scores["CompanyName"]))

# pick best phone column
phone_col = None
if phone_candidates:
    phone_col = max(phone_candidates, key=lambda x: x[1])[0]

# pick best company column
company_col = None
if company_candidates:
    company_col = max(company_candidates, key=lambda x: x[1])[0]

# prepare output
out_df = df.copy()

if phone_col:
    out_df["Country"] = df[phone_col].apply(lambda x: parse_phone(str(x), countries_list)[0])
    out_df["Number"] = df[phone_col].apply(lambda x: parse_phone(str(x), countries_list)[1])

if company_col:
    out_df["Name"] = df[company_col].apply(lambda x: parse_company(str(x), legal_list)[0])
    out_df["Legal"] = df[company_col].apply(lambda x: parse_company(str(x), legal_list)[1])

out_df.to_csv("output.csv", index=False)
print("output.csv created!")
