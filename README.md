# GitHub Trend Tracker · `update-script-and-dbt`

> Refactoring manual SQL-in-Python transforms into a dbt incremental model on BigQuery.

---

## What This Branch Does

This branch refactors the original `main` baseline into a cleaner, more scalable architecture — separating data ingestion from transformation, and replacing manual SQL strings with proper dbt models.

---

## Architecture: Before vs. After

| | `main` (Baseline) | `update-script-and-dbt` (This Branch) |
|---|---|---|
| **Transform Layer** | Hardcoded SQL inside Python | Dedicated `.sql` models in dbt |
| **Data Updates** | Manual `UPSERT / MERGE` logic | `materialized='incremental'` in dbt |
| **Architecture Style** | Imperative (step-by-step scripts) | Declarative (define the end state) |
| **Separation of Concerns** | Mixed extract + transform | Python = EL, dbt = T |

---

## Key Changes

**Incremental Modeling**  
`fct_github_trends.sql` uses `materialized='incremental'`, so dbt appends only new daily snapshots rather than rebuilding the entire table on every run. No more manual merge logic.

**Separation of Concerns**  
Python handles extraction from the GitHub API and loading into BigQuery. dbt takes it from there — keeping the two responsibilities cleanly separated.

**Repo Refactoring**  
Moved to a root-level dbt project structure to make future orchestration (e.g. Airflow, dbt Cloud) straightforward.

---

## Running the Pipeline

```bash
# 1. Fetch raw data from the GitHub API and land it in BigQuery
python pipeline.py

# 2. Run the incremental dbt transformation
dbt run --select fct_github_trends
```

---

## Stack

`Python` · `BigQuery` · `dbt Core` · `GitHub API`

---

Part of an ongoing project to track GitHub trending repositories over time.
