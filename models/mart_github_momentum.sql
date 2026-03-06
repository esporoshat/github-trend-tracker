{{ config(materialized='table') }}

with daily_growth as (
    select
        repo_name,
        snapshot_date,
        stars,
        stars_added_today,
        growth_velocity_pct
    --we ref the mart, not the fct
    from {{ ref('mart_github_daily_metrics') }}
    where stars_added_today is not null
),

repo_stats as (
    select
        repo_name,
        snapshot_date,
        stars,
        stars_added_today,
        growth_velocity_pct,
        -- rolling 7-day average growth for this repo
        avg(stars_added_today) over (
            partition by repo_name
            order by snapshot_date asc
            rows between 6 preceding and current row
        ) as avg_stars_7d,
        -- rolling 7-day standard deviation
        stddev(stars_added_today) over (
            partition by repo_name
            order by snapshot_date asc
            rows between 6 preceding and current row
        ) as stddev_stars_7d
    from daily_growth
)

select
    repo_name,
    snapshot_date,
    stars,
    stars_added_today,
    growth_velocity_pct,
    round(avg_stars_7d, 2)    as avg_stars_7d,
    round(stddev_stars_7d, 2) as stddev_stars_7d,
    -- momentum score: how many standard deviations above normal is today?
    case
        when stddev_stars_7d is null or stddev_stars_7d = 0 then null
        else round((stars_added_today - avg_stars_7d) / stddev_stars_7d, 2)
    end as momentum_score,
    current_timestamp() as mart_updated_at

from repo_stats