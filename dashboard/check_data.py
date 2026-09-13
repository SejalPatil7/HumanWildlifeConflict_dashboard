import pandas as pd

df = pd.read_csv("../data/processed/incidents.csv")

print(df.columns.tolist())
print("\nRows:", len(df))

print("\nMissing values:")
print(df.isna().sum())

print("\nSpecies:")
print(df["species"].value_counts())

print("\nConflict types:")
print(df["conflict_type"].value_counts())

print("\nStates:")
print(df["state"].value_counts())