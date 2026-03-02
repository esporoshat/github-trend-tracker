{{
  config(
    materialized='incremental',
    on_schema_change='append_new_columns'
  )
}}

select
    repo_name,
    stars,
    forks,
    open_issues,
    language,
    description,
    pushed_at,
    last_updated,
    snapshot_date
from {{ source('raw_github_data', 'top_repos_staging') }}

{% if is_incremental() %}
  -- this filter ensures we don't accidentally pull in data 
  -- that is already in our historical table
  where snapshot_date > (select max(snapshot_date) from {{ this }})
{% endif %}