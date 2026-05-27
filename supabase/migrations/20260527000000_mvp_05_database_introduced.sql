create table if not exists app_config (
    key text primary key,
    value text not null default '',
    is_secret boolean not null default false,
    topic text not null default 'general',
    updated_at timestamptz not null default now()
);

create table if not exists portfolio_snapshots (
    id uuid primary key default gen_random_uuid(),
    provider text not null,
    source text not null,
    captured_at timestamptz not null default now()
);

create table if not exists portfolio_holdings (
    id uuid primary key default gen_random_uuid(),
    snapshot_id uuid not null references portfolio_snapshots(id) on delete cascade,
    provider text not null,
    section text not null,
    symbol text not null,
    name text not null,
    quantity numeric not null default 0,
    currency text not null,
    market_value numeric not null default 0,
    cost_basis numeric,
    captured_at timestamptz not null default now()
);

create table if not exists portfolio_cash (
    id uuid primary key default gen_random_uuid(),
    snapshot_id uuid not null references portfolio_snapshots(id) on delete cascade,
    provider text not null,
    currency text not null,
    amount numeric not null default 0,
    captured_at timestamptz not null default now()
);

create table if not exists version_log (
    id bigserial primary key,
    version text not null,
    title text not null,
    created_at timestamptz not null default now()
);

create table if not exists genai_conversations (
    id uuid primary key default gen_random_uuid(),
    role text not null check (role in ('user', 'assistant')),
    content text not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_portfolio_holdings_captured_at on portfolio_holdings(captured_at desc);
create index if not exists idx_portfolio_cash_captured_at on portfolio_cash(captured_at desc);
create index if not exists idx_portfolio_snapshots_provider_captured_at on portfolio_snapshots(provider, captured_at desc);

insert into app_config (key, value, topic, is_secret) values
('default_display_currency', 'EUR', 'general', false),
('investor_profile', 'Long-term investor focused on diversified growth.', 'investor_profile', false),
('investment_objectives', 'Capital appreciation and diversification.', 'investor_profile', false),
('risk_tolerance', 'moderate', 'investor_profile', false),
('investment_horizon', '10+ years', 'investor_profile', false),
('binance_api_key', '', 'api_keys', true),
('binance_api_secret', '', 'api_keys', true),
('binance_base_url', 'https://api.binance.com', 'api_keys', false),
('genai_provider', 'disabled', 'genai', false),
('genai_model', '', 'genai', false),
('google_api_key', '', 'api_keys', true),
('openai_api_key', '', 'api_keys', true),
('anthropic_api_key', '', 'api_keys', true),
('exchangerate_host_url', 'https://api.exchangerate.host', 'general', false),
('asset_insight_prompt', 'Analyze this asset for the investor. Asset: {asset}. Portfolio context: {portfolio}. Investor profile: {investor_profile}. Return concise facts, interpretation, risks, fit, and action options.', 'prompts', false),
('asset_macro_prompt', 'Analyze the current macro, industry, and market context relevant to this asset. Asset: {asset}. Investor profile: {investor_profile}. Return concise implications for holding, adding, trimming, or monitoring.', 'prompts', false),
('portfolio_insight_prompt', 'Analyze the portfolio as a system using this portfolio context: {portfolio}. Investor profile: {investor_profile}. Return executive insights, risks, diversification gaps, and practical recommendations.', 'prompts', false),
('asset_compare_prompt', 'Compare the original asset with similar alternatives. Original asset: {asset}. Investor profile: {investor_profile}. Return a complete responsive HTML table only. Columns are assets, first column is the original asset. Rows should include ticker, asset type, market/industry, thesis, quality, valuation context, growth, risk, portfolio fit, pros, cons, confidence, and conclusion.', 'prompts', false),
('chat_extra_context', 'Answer as an educational portfolio assistant. Be concise, practical, and aware of portfolio and investor fit.', 'prompts', false)
on conflict (key) do nothing;

insert into version_log (version, title, created_at) values
('MVP v0.5', 'database introduced', '2026-05-27T00:00:00Z'),
('MVP v0.3.4', 'Automated GenAI insights and persistent portfolio chat', '2026-05-26T00:00:00Z'),
('MVP v0.3.3', 'Env vars adjustments', '2026-05-25T00:00:00Z'),
('MVP v0.3.2', 'UX improvements', '2026-05-24T00:00:00Z'),
('MVP v0.3.1', 'Code corrections', '2026-05-23T00:00:00Z'),
('MVP v0.3', 'added version log', '2026-05-22T00:00:00Z'),
('MVP v0.2', 'extending the draft', '2026-05-21T00:00:00Z'),
('MVP v0.1', 'MVP initial draft', '2026-05-20T00:00:00Z')
on conflict do nothing;
