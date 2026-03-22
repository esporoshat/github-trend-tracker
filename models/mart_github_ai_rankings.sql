{{ config(materialized='table') }}

with ranked as (
    select
        repo_name,
        snapshot_date,
        stars,
        forks,
        language,
        -- rank repos by stars on each day
        rank() over (
            partition by snapshot_date
            order by stars desc
        ) as daily_rank
    from {{ ref('fct_github_trends') }}
),

rank_lag as (
    select
        repo_name,
        snapshot_date,
        stars,
        forks,
        language,
        daily_rank,
        lag(daily_rank) over (
            partition by repo_name
            order by snapshot_date asc
        ) as prev_rank
    from ranked
)

select
    repo_name,
    snapshot_date,
    stars,
    forks,
    language,
    daily_rank,
    prev_rank,
    -- positive = moved up, negative = moved down, null = first appearance
    case
        when prev_rank is null then null
        else prev_rank - daily_rank
    end as rank_change,
    case
        when prev_rank is null then 'new_entry'
        when prev_rank - daily_rank > 0 then 'rising'
        when prev_rank - daily_rank < 0 then 'falling'
        else 'stable'
    end as rank_status,
    current_timestamp() as mart_updated_at

from rank_lag