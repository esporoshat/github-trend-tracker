import requests
from google.cloud import bigquery
from datetime import date 
import pandas as pd
import os
from dotenv import load_dotenv

# This looks for the .env file and loads the variables
load_dotenv()

####fetching data from GitHub API using a personal access token (PAT) for authentication####
github_token = os.getenv("GITHUB_TOKEN")
headers = {"Authorization": "token " + github_token}

# -----------------------------
# 1 GitHub API call
# -----------------------------
url = "https://api.github.com/search/repositories"

params = {
    "q": "topic:ai created:>2026-01-01",  # search repos with topic AI created after Jan 1, 2026
    "sort": "stars",                      # sort by stars (popularity)
    "order": "desc",                      # descending order → most stars first
    "per_page": 5                         # only top 5 results
}


response = requests.get(url, headers=headers, params=params)

# Check for errors
if response.status_code != 200:
    print("Error:", response.status_code, response.text)
    exit()

data = response.json()

# Print results
for repo in data['items']:
    print(f"Name: {repo['name']}, Stars: {repo['stargazers_count']}, Forks: {repo['forks_count']}")

# -----------------------------
# 2️ BigQuery client setup
# -----------------------------
client = bigquery.Client() # This will use the GOOGLE_APPLICATION_CREDENTIALS env variable for auth

project_id = "github-trend-tracker-488210"
dataset_id = "github_trends"
table_id = "top_repos"

# -----------------------------
# 3️ Create dataset if missing
# -----------------------------
dataset_ref = f"{project_id}.{dataset_id}"
dataset = bigquery.Dataset(dataset_ref)
dataset.location = "europe-west3"  # Frankfurt
client.create_dataset(dataset, exists_ok=True)
print(f"Dataset '{dataset_id}' created or already exists in Frankfurt.")

# -----------------------------
# 4️ Create table if missing
# -----------------------------
table_ref = f"{dataset_ref}.{table_id}"

schema = [
    bigquery.SchemaField("repo_name", "STRING"),
    bigquery.SchemaField("stars", "INTEGER"),
    bigquery.SchemaField("forks", "INTEGER"),
    bigquery.SchemaField("language", "STRING"), # Optional field for programming language,
    bigquery.SchemaField("description", "STRING"), # Optional field for repository description  
    bigquery.SchemaField("html_url", "STRING"), # Optional field for repository URL 
    bigquery.SchemaField("last_updated", "TIMESTAMP"), # Optional field for last update time
    bigquery.SchemaField("snapshot_date", "DATE"),
]

table = bigquery.Table(table_ref, schema=schema)
client.create_table(table, exists_ok=True)
print(f"Table '{table_id}' created or already exists.")

# -----------------------------
# 5️ Prepare rows and load in batch
# -----------------------------
rows_to_insert = []
today = date.today()

for repo in data['items']:
    rows_to_insert.append({
        "repo_name": repo["name"],
        "stars": repo["stargazers_count"],
        "forks": repo["forks_count"],
        "language": repo["language"],
        "description": repo["description"],
        "html_url": repo["url"],
        "last_updated": repo["updated_at"], 
        "snapshot_date": today
    })

# Convert to DataFrame
df = pd.DataFrame(rows_to_insert)

#------------------------------
# 6 Load to Staging with WRITE_TRUNCATE (overwrites existing data)
#------------------------------
staging_table_id = f"{project_id}.{dataset_id}.top_repos_staging"

job_config = bigquery.LoadJobConfig(
    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
)

load_job = client.load_table_from_dataframe(df, staging_table_id, job_config=job_config)

load_job.result()
print(f"Data loaded to staging table {staging_table_id} with WRITE_TRUNCATE")

#-----------------------------
# 7️ Move from staging to final with MERGE to handle updates and inserts
#-----------------------------
production_table_id = f"{project_id}.{dataset_id}.{table_id}"

merge_query = f"""
MERGE `{production_table_id}` TARGET
USING `{staging_table_id}` SOURCE
ON TARGET.repo_name = SOURCE.repo_name
AND TARGET.snapshot_date = SOURCE.snapshot_date
WHEN MATCHED THEN
  UPDATE SET
  stars = SOURCE.stars,
  forks = SOURCE.forks,
  language = SOURCE.language,
  description = SOURCE.description,
  last_updated = CAST(SOURCE.last_updated AS TIMESTAMP)
WHEN NOT MATCHED THEN
    INSERT (repo_name, stars, forks, language, description, html_url, last_updated, snapshot_date)
    VALUES (SOURCE.repo_name, SOURCE.stars, SOURCE.forks, SOURCE.language, SOURCE.description, SOURCE.html_url, CAST(SOURCE.last_updated AS TIMESTAMP), SOURCE.snapshot_date)
"""

merge_job = client.query(merge_query)
merge_job.result()
print(f"Data merged from staging to production table {production_table_id}.")