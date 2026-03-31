-- MSME Credit Scoring — Supabase Schema
-- Run: supabase db push

-- Customers / businesses
create table if not exists public.businesses (
    id              uuid primary key default gen_random_uuid(),
    business_id     text unique not null,
    country_code    text not null,
    sector          text not null,
    registered_at   timestamptz default now(),
    updated_at      timestamptz default now()
);

-- Scoring history (full audit trail)
create table if not exists public.scoring_logs (
    id                  uuid primary key default gen_random_uuid(),
    business_id         text not null references public.businesses(business_id),
    credit_score        integer not null check (credit_score between 300 and 850),
    default_probability numeric(6,4) not null,
    risk_band           text not null check (risk_band in ('A', 'B', 'C', 'D')),
    decision            text not null check (decision in ('approved', 'review', 'declined')),
    requested_amount    numeric(18,2),
    max_loan_amount     numeric(18,2),
    model_version       text not null,
    scored_at           timestamptz default now(),
    features_snapshot   jsonb  -- store features used for full reproducibility
);

-- Active credit scores (latest per business)
create or replace view public.current_scores as
select distinct on (business_id)
    business_id,
    credit_score,
    default_probability,
    risk_band,
    decision,
    scored_at
from public.scoring_logs
order by business_id, scored_at desc;

-- Portfolio risk summary (materialized for dashboards)
create materialized view if not exists public.portfolio_risk_summary as
select
    risk_band,
    count(*)                        as customer_count,
    round(avg(credit_score), 0)     as avg_score,
    round(avg(default_probability) * 100, 2) as avg_default_pct,
    sum(max_loan_amount)            as total_approved_exposure
from public.current_scores
group by risk_band;

-- RLS (Row Level Security) — important for multi-tenant setup
alter table public.scoring_logs enable row level security;
alter table public.businesses enable row level security;

-- Allow service role full access
create policy "service_role_all" on public.scoring_logs
    for all using (auth.role() = 'service_role');

create policy "service_role_all" on public.businesses
    for all using (auth.role() = 'service_role');
