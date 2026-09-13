import pandas as pd

df = pd.read_csv("../data/processed/incidents.csv")

print(df.columns.tolist())
print(df.head())
print("Rows:", len(df))