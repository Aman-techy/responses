import pandas as pd

url = "https://docs.google.com/spreadsheets/d/1PIhDB-RqQguZl6kGb19_ZkXcVvMYJwMmflgaiZ0PDDQ/export?format=csv"

try:
    df = pd.read_csv(url)
    print("Columns:", df.columns.tolist())
    print("First few rows:")
    print(df.head())
    print("Dtypes:")
    print(df.dtypes)
except Exception as e:
    print(f"Error reading CSV: {e}")
