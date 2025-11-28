from fastapi import FastAPI, Form
import pandas as pd
import os

app = FastAPI()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

@app.get("/files")
def list_files():
    return {"files": os.listdir(DATA_DIR)}

@app.post("/predict")
def predict(file_name: str = Form(...), column: str = Form(...)):
    file_path = os.path.join(DATA_DIR, file_name)

    if not os.path.exists(file_path):
        return {"error": f"File '{file_name}' not found"}

    df = pd.read_csv(file_path)

    if column not in df.columns:
        return {"error": f"Column '{column}' not found in {file_name}"}

    values = df[column].unique().tolist()

    return {"unique_values": values}
