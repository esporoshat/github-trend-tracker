<div align="center">

#  GitHub Trend Tracker

**An automated data pipeline that captures the pulse of the open-source ecosystem — daily.**

</div>

---

##  What It Does

This project is a **production-style ETL pipeline** that automatically fetches the top trending repositories (created after 1st of January 2026) from GitHub and lands them in **Google BigQuery** for long-term analysis.

Every run takes a daily snapshot — capturing stars, forks, and metadata — so you can track *what the developer world is paying attention to* over time.

> Think of it as a time-series lens on open-source momentum.

---

##  Tech Stack

| Layer | Technology | Role |
|---|---|---|
| **Language** | Python 3.11+ | Pipeline orchestration & API calls |
| **Data Source** | GitHub REST API | Trending repo metadata |
| **Data Warehouse** | Google BigQuery | Scalable cloud storage & querying |
| **Upsert Logic** | SQL `MERGE` statements | Idempotent, safe re-runs |

---

##  Architecture at a Glance

```
GitHub REST API
      │
      ▼
  pipeline.py          ← Fetches, transforms, and loads
      │
      ▼
  SQL MERGE Logic      ← Upserts into BigQuery (no duplicates)
      │
      ▼
  Google BigQuery      ← Queryable historical snapshots
```

---

##  Local Setup

> This repo excludes secrets intentionally. Here's how to wire it up locally:

**1. Clone the repo**
```bash
git clone https://github.com/your-username/github-trend-tracker.git
cd github-trend-tracker
```

**2. Create your `.env` file**
```bash
# .env
GITHUB_TOKEN=your_personal_access_token_here
```

**3. Add your Google Cloud credentials**

Place your BigQuery Service Account JSON key in the root directory and ensure the filename matches the path referenced in `pipeline.py`.

**4. Install dependencies & run**
```bash
pip install -r requirements.txt
python pipeline.py
```

> 🔒 Both `.env` and `*.json` files are listed in `.gitignore` — secrets never leave your machine.

---


<div align="center">

*Built to explore what the open-source world is excited about — one snapshot at a time.*

</div>
