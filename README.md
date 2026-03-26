#  GitHub Trend Tracker

> A fully automated data pipeline that wakes up every morning, fetches the most-starred AI repositories on GitHub, and transforms the raw data into analytics-ready tables. All without touching a single button.

---

##  What Does It Do?

Every day at **9:00 AM UTC**, a GitHub Actions workflow kicks off a two-step pipeline:

1. **Extract & Load** — `pipeline.py` calls the GitHub API, pulls the top AI repositories by star count, and loads the raw data into **Google BigQuery**
2. **Transform** — `dbt` picks up from there and builds a clean set of models: from a historical fact table all the way to momentum scoring

The result is a growing, day-by-day record of which AI repos are rising, falling, or exploding in popularity.

---

##  Architecture

```
GitHub API
    │
    ▼
pipeline.py  ──►  BigQuery (top_repos_staging)   [WRITE_TRUNCATE — fresh daily snapshot]
                        │
                        ▼
                 dbt (fct_github_trends)          [Incremental — appends new dates only]
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
   ai_rankings    daily_metrics   momentum       [Mart layer — analytics-ready tables]
```

---

##  Data Models

### `fct_github_trends` — The Foundation
The core historical table. Each row is one repository on one day (`repo_name + snapshot_date`). Built as an **incremental model**, so dbt only appends new dates. it never rewrites history.

| Column | Description |
|---|---|
| `repo_snapshot_id` | Unique key: `repo_name-YYYY-MM-DD` |
| `repo_name`, `stars`, `forks` | Core repo metrics |
| `language`, `topics`, `description` | Metadata |
| `snapshot_date` | The date this snapshot was taken |

---

### `mart_github_daily_metrics` — Growth Layer
Adds day-over-day star growth on top of the fact table.

| Column | Description |
|---|---|
| `stars_added_today` | Absolute star gain since yesterday |
| `growth_velocity_pct` | Percentage growth vs. the day before |

---

### `mart_github_ai_rankings` — Leaderboard
Ranks every repository by star count for each day and tracks movement.

| Column | Description |
|---|---|
| `daily_rank` | Star-based rank for that day |
| `rank_change` | How many positions moved vs. yesterday |
| `rank_status` | `rising` / `falling` / `stable` / `new_entry` |

---

### `mart_github_momentum` — Trend Detection
The most analytical layer. Uses a **7-day rolling window** to calculate a Z-score momentum metric. It answers: *"Is today's growth unusual compared to this repo's own recent history?"*

| Column | Description |
|---|---|
| `avg_stars_7d` | Rolling 7-day average star growth |
| `stddev_stars_7d` | Rolling 7-day standard deviation |
| `momentum_score` | Z-score: how many std deviations above normal today was |

A `momentum_score` above 2.0 means a repo is having an unusually big day.

---

##  Automation — GitHub Actions

The entire pipeline runs on a schedule with **zero manual steps**:

```yaml
on:
  schedule:
    - cron: '0 9 * * *'   # Every day at 9:00 AM UTC
  workflow_dispatch:       # Manual trigger available too
```

Each run:
1. Spins up a fresh Ubuntu runner
2. Installs Python dependencies + `dbt-bigquery`
3. Writes GCP credentials from a GitHub Secret (no keys stored in code)
4. Runs `pipeline.py` → then `dbt run`

Credentials are handled entirely through **GitHub Secrets** — `GCP_SA_KEY` and `GH_TOKEN` — so nothing sensitive ever lives in the repository.

---

##  Data Quality

Tests are defined in `schema.yml` and run as part of the dbt layer:

| Model | Test |
|---|---|
| `fct_github_trends` | `repo_snapshot_id` is unique and not null |
| `mart_github_ai_rankings` | `repo_name` and `daily_rank` are not null |
| `mart_github_ai_rankings` | `rank_status` only contains expected values |
| `mart_github_daily_metrics` | `repo_name` and `snapshot_date` are not null |

---

##  Tech Stack

| Layer | Tool |
|---|---|
| Orchestration | GitHub Actions |
| Extraction | Python 3.12 + `requests` + `tenacity` |
| Storage | Google BigQuery (europe-west3 / Frankfurt) |
| Transformation | dbt (BigQuery adapter) |
| Retry logic | `tenacity` — 3 attempts with exponential backoff |
| Auth | Service account via GitHub Secrets |

---

##  Project Structure

```
├── pipeline.py                  # Extraction + BigQuery load
├── requirements.txt
├── models/
│   ├── sources.yml              # Points dbt to the raw BigQuery table
│   ├── schema.yml               # Data quality tests
│   ├── fct_github_trends.sql    # Incremental fact table
│   ├── mart_github_daily_metrics.sql
│   ├── mart_github_ai_rankings.sql
│   └── mart_github_momentum.sql
├── profiles.yml                 # dbt connection config (env-variable driven)
└── .github/
    └── workflows/
        └── pipeline.yml         # The daily schedule
```

---

##  How to Run It Locally

**1. Clone the repo and install dependencies**
```bash
git clone https://github.com/your-username/github-trend-tracker.git
cd github-trend-tracker
pip install -r requirements.txt
pip install dbt-bigquery
```

**2. Set your environment variables**
```bash
export GITHUB_TOKEN=your_github_pat
export GOOGLE_APPLICATION_CREDENTIALS=path/to/your/creds.json
export GCP_PROJECT_ID=your-gcp-project-id
export DBT_DATASET=github_trends
```

**3. Run the pipeline**
```bash
python pipeline.py
dbt run
dbt test
```

---

##  Design Decisions Worth Noting

**Why a staging table with `WRITE_TRUNCATE`?**
The GitHub API only gives a snapshot of *right now*. The staging table is overwritten every day on purpose. It's a landing zone, not a store. History lives in `fct_github_trends`.

**Why incremental dbt?**
So the fact table only grows. Each day's snapshot is appended once and never touched again. If dbt reruns, it won't duplicate data.

**Why Z-score for momentum?**
Raw star counts are misleading. A repo with 50,000 stars gaining 200 in a day is less interesting than a 500-star repo gaining 80. The Z-score normalizes growth against each repo's own history, making comparisons fair.


