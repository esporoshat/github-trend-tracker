import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
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


# If this function fails, try again!
@retry(
    stop=stop_after_attempt(3), # Stop after 3 tries
    wait=wait_exponential(multiplier=1, min=4, max=10), # Wait 4s, then 8s, then 10s
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)

def fetch_github_data(url, headers, params):
    response = requests.get(url, headers=headers, params=params)
    
    # Raise an error if the status is 4xx or 5xx so tenacity knows to retry
    response.raise_for_status() 
    
    return response.json()


try:
    data = fetch_github_data(url, headers, params)
    print("Successfully fetched data!")
except Exception as e:
    print(f"Permanent Failure after 3 attempts: {e}")
    exit(1)
    
# -----------------------------
# 2️ BigQuery client setup
# -----------------------------
client = bigquery.Client()  # This will use the GOOGLE_APPLICATION_CREDENTIALS env variable for auth

project_id = "github-trend-tracker-488210"
# This looks for 'DBT_DATASET'. If not found, it defaults to 'github_trends'
dataset_id = os.getenv("DBT_DATASET", "github_trends")
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

# Check if items actually exist before looping
if not data.get('items'):
    print("No repositories found for this query.")
else:
    for repo in data['items']:
        rows_to_insert.append({
            "repo_name": repo.get("name"),
            "stars": repo.get("stargazers_count"),
            "forks": repo.get("forks_count"),
            "open_issues": repo.get("open_issues_count"),
            "language": repo.get("language"),
            "description": repo.get("description"),
            "pushed_at": repo.get("pushed_at"),
            "last_updated": repo.get("updated_at"), 
            "topics": repo.get("topics", []),  ## captures all topics as an array,
            "repo_url": repo.get("html_url"),  # Browser-friendly link
            "snapshot_date": today,
            # To add a new column in the future, just add one line here:
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

