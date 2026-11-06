{% snapshot members_snapshot %}

{{ config(
    target_schema='dbt',
    unique_key='member_id',
    strategy='check',
    check_cols='all'
) }}

select * from {{ ref('stg_members') }}

{% endsnapshot %}