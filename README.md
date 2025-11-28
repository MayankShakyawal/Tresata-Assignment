# IIT Madras – Tresata Assignment
**Student:** *Your Name*  
**Parts Completed:** Part A & Part B (Core Requirements)

## 🧩 Project Overview
This project implements:

### **1️ Part A — Column Type Prediction (predict.py)**
A Python script that analyzes a column in a CSV file and predicts the type of data it contains:
- 📱 Phone Number  
- 🏢 Company Name  
- 🌍 Country  
- 📅 Date  
- 🔣 Other (fallback)

### **2️ Part B — Data Parsing Tool (parser.py)**
A Python script that:
- Automatically identifies the column containing Phone Numbers or Company Names  
- Parses entries into structured components  
- Generates an `output.csv` file  

##  Folder Structure
```
IITM-Data-Parser-Assignment/
│
├── data/
│
├── tools/
│   ├── predict.py
│   ├── parser.py
│
├── mcp_package/
│
├── server
├── requirements.txt
└── README.md
```

##  Installation
```
pip install -r requirements.txt
```

## Running the Scripts

### Part A:
```
python tools/predict.py --input <path/to/input.csv> --column <column_name>
```

### Part B:
```
python tools/parser.py --input <path/to/input.csv>
```

