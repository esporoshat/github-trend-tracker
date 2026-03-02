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
client = bigquery.Client.from_service_account_json(
    "/Users/poroshat/Desktop/github-trend-tracker/github-trend-tracker-488210-89ebbc40a855.json"
)

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
# 4️ Dynamic table handling
# -----------------------------
table_ref = f"{dataset_ref}.{table_id}"

# We no longer need to define 'schema = [...]' manually here.
# If the table doesn't exist, BigQuery will create it based on the first DataFrame upload.
# If it does exist, we'll let it evolve.

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
    autodetect=True,  # Let BigQuery infer the schema from the DataFrame
    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
)

load_job = client.load_table_from_dataframe(df, staging_table_id, job_config=job_config)

load_job.result()
print(f"Data loaded to staging table {staging_table_id} with WRITE_TRUNCATE")

