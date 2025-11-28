
import pandas as pd
import argparse
import re
import os

# -------- Helper Functions -------- #

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
    date_patterns = [
        r'^\d{2}[-/\.]\d{2}[-/\.]\d{4}$',
        r'^\d{4}[-/\.]\d{2}[-/\.]\d{2}$',
        r'^\d{8}$',
        r'^\d{1,2}[-/\.]\w{3}[-/\.]\d{4}$'
    ]
    for p in date_patterns:
        if re.match(p, value.strip()):
            return True
    return False

def is_company(value, legal_set):
    if not isinstance(value, str):
        return False
    lower = value.lower()
    for ls in legal_set:
        if ls and ls in lower:
            return True
    return False

def predict_column_type(values, countries_list, legal_list):
    sample = [str(v) for v in values[:100] if str(v).strip() != ""]
    
    country_set = set([c.lower().strip() for c in countries_list])
    legal_set = set([l.lower().strip() for l in legal_list])

    phone_score = sum(is_phone(v) for v in sample)
    country_score = sum(is_country(v, country_set) for v in sample)
    date_score = sum(is_date(v) for v in sample)
    company_score = sum(is_company(v, legal_set) for v in sample)

    scores = {
        "PhoneNumber": phone_score,
        "Country": country_score,
        "Date": date_score,
        "CompanyName": company_score,
        "Other": 0
    }

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "Other"
    return best


# -------- Main Program -------- #

parser = argparse.ArgumentParser()
parser.add_argument("--input", type=str, required=True)
parser.add_argument("--column", type=str, required=True)
args = parser.parse_args()

# Detect resource folder
resource_folder = os.path.dirname(__file__)

countries_list = open(os.path.join(resource_folder, "countries.txt")).read().strip().split("\n")
legal_list = open(os.path.join(resource_folder, "legal.txt")).read().strip().split("\n")

df = pd.read_csv(args.input)

if args.column not in df.columns:
    print("ERROR: Column not found")
    exit()

column_values = df[args.column].tolist()
result = predict_column_type(column_values, countries_list, legal_list)

print(result)
