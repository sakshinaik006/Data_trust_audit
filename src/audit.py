from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "adult"/"adult.data"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

COLUMNS = [
    "age", "workclass", "fnlwgt", "education", "education_num",
    "marital_status", "occupation", "relationship", "race", "sex",
    "capital_gain", "capital_loss", "hours_per_week",
    "native_country", "income",
]
NUMERIC = ["age", "fnlwgt", "education_num", "capital_gain",
           "capital_loss", "hours_per_week"]
CATEGORICAL = [c for c in COLUMNS if c not in NUMERIC]

AGE_RANGE = (17, 100)
HOURS_RANGE = (1, 100)

df = pd.read_csv(DATA, header=None, names=COLUMNS,
                 na_values=["?", " ?"])
print("Shape:", df.shape)
print(df.head())

missing = pd.DataFrame({
    "missing_count": df.isna().sum(),
    "missing_percent": (df.isna().mean() * 100).round(2),
})
missing.index.name = "column"
missing.to_csv(REPORTS / "missing_values.csv")

dupes = df[df.duplicated(keep=False)]
print("\nSample duplicate rows:")
print(dupes.sort_values(COLUMNS).head(6))

rows = []
for col in CATEGORICAL:
    s = df[col].dropna()
    stripped = s.str.strip()
    rows.append({
        "column": col,
        "unique_raw": s.nunique(),
        "unique_after_strip": stripped.nunique(),
        "unique_after_strip_lower": stripped.str.lower().nunique(),
        "values_with_extra_whitespace": int((s != stripped).sum()),
    })
category_report = pd.DataFrame(rows)
category_report.to_csv(REPORTS / "category_consistency.csv", index=False)

outliers = []
for col in NUMERIC:
    q1, q3 = df[col].quantile([0.25, 0.75])
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outliers.append({
        "column": col,
        "lower_bound": lower,
        "upper_bound": upper,
        "flagged_count": int(((df[col] < lower) | (df[col] > upper)).sum()),
    })
pd.DataFrame(outliers).to_csv(REPORTS / "outlier_review.csv", index=False)


def whitespace_count(frame):
    total = 0
    for col in CATEGORICAL:
        s = frame[col].dropna()
        total += int((s != s.str.strip()).sum())
    return total


def education_conflicts(frame):
    labels = frame["education"].str.strip()
    return int((frame.groupby(labels)["education_num"].nunique() > 1).sum())


def metrics(frame):
    return {
        "Total records": len(frame),
        "Exact duplicate rows": int(frame.duplicated().sum()),
        "Missing cells": int(frame.isna().sum().sum()),
        "Rows with at least one missing value": int(frame.isna().any(axis=1).sum()),
        "Invalid age records": int((~frame["age"].between(*AGE_RANGE)).sum()),
        "Invalid working-hours records": int(
            (~frame["hours_per_week"].between(*HOURS_RANGE)).sum()),
        "Category values with extra whitespace": whitespace_count(frame),
        "Education label/code conflicts": education_conflicts(frame),
    }


clean = df.copy()
for col in CATEGORICAL:
    clean[col] = clean[col].str.strip()
clean = clean.drop_duplicates()
clean.to_csv(REPORTS / "cleaned_data.csv", index=False)

before, after = metrics(df), metrics(clean)
summary = pd.DataFrame({
    "Metric": list(before.keys()),
    "Before cleaning": list(before.values()),
    "After cleaning": list(after.values()),
})
summary.to_csv(REPORTS / "audit_summary.csv", index=False)

income_cmp = pd.concat(
    [df["income"].str.strip().value_counts(normalize=True) * 100,
     clean["income"].value_counts(normalize=True) * 100],
    axis=1, keys=["before_pct", "after_pct"],
).round(2)
income_cmp.to_csv(REPORTS / "income_before_after.csv")

hours_before = round(df["hours_per_week"].mean(), 3)
hours_after = round(clean["hours_per_week"].mean(), 3)

plot_data = missing[missing["missing_count"] > 0]["missing_count"].sort_values()
if not plot_data.empty:
    plot_data.plot(kind="barh", figsize=(8, 5))
    plt.title("Missing Values by Column")
    plt.xlabel("Number of Missing Values")
    plt.tight_layout()
    plt.savefig(REPORTS / "missing_values.png", dpi=150)
    plt.close()

print("\nTop capital_gain values:")
print(df["capital_gain"].value_counts().head())
print("Rows with capital_gain == 99999:", int((df["capital_gain"] == 99999).sum()))

both_missing = int(df[["workclass", "occupation"]].isna().all(axis=1).sum())
either_missing = int(df[["workclass", "occupation"]].isna().any(axis=1).sum())
print(f"\nworkclass & occupation both missing: {both_missing}")
print(f"workclass or occupation missing:      {either_missing}")

print("\nDATA QUALITY AUDIT")
print(summary.to_string(index=False))
print("\nMissing values:")
print(missing[missing["missing_count"] > 0])
print("\nCategory consistency:")
print(category_report.to_string(index=False))
print("\nIncome distribution (%):")
print(income_cmp)
print(f"\nMean hours/week: before={hours_before}, after={hours_after}")
print(f"\nReports saved to: {REPORTS}")

print(df.groupby(df["workclass"].isna())["income"].value_counts(normalize=True).round(3))