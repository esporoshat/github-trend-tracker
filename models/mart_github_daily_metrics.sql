{{ config(materialized='table') }}

with daily_lag as (
    select
        repo_name,
        snapshot_date,
        stars,
        forks,
        open_issues,
        -- We grab the previous day's stars to calculate the delta
        lag(stars) over (partition by repo_name order by snapshot_date asc) as prev_stars
    from {{ ref('fct_github_trends') }}
)

select
    repo_name,
    snapshot_date,
    stars,
    forks,
    open_issues,
    -- Metric 1a: Absolute Growth
    stars - coalesce(prev_stars, 0) as stars_added_today,
    
    -- Metric 1b: Growth Velocity (%)
    case 
        when prev_stars is null or prev_stars = 0 then null 
        else ((stars - prev_stars) / prev_stars) * 100 
    end as growth_velocity_pct,

    current_timestamp() as mart_updated_at
from daily_lag