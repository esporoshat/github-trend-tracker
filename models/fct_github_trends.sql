{{
  config(
    materialized='incremental',
    unique_key='repo_snapshot_id',
    on_schema_change='append_new_columns'
  )
}}

select
    -- 1. We define the new unique ID here
    concat(repo_name, '-', cast(snapshot_date as string)) as repo_snapshot_id,
    
    -- 2. Then we list the rest of the original columns
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