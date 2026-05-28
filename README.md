# Pythagoras Portfolio Manager

A Python FastAPI investment dashboard with a PostgreSQL-backed configuration layer, portfolio snapshots, version log, and separated GenAI features.

## Features

- Central dashboard with three sections: Shares, Funds, Cryptos
- Portfolio evolution history with historical value tracking
- Holdings and cash totals overall and by provider
- Currency display as native, EUR, or USD
- Binance account balance integration using signed REST API calls
- DEGIRO CSV import for:
  - Portfolio overview
  - Account statement
  - Transaction statement upload storage
- Persistent PostgreSQL database (Supabase compatible) for:
  - App configuration with topic separation
  - Portfolio snapshots and evolution
  - Version log
  - Persistent GenAI conversation history
- Full configuration page split by topics:
  - General settings
  - Investor profile
  - API keys
  - GenAI settings
  - Custom prompts
- GenAI integration with selectable provider:
  - Google Gemini
  - OpenAI
  - Anthropic
- Separated GenAI features:
  - Asset-specific insights per holding
  - Macro-economic analysis per asset
  - Portfolio-level insights
  - Similar-asset comparison with generated HTML tables
  - Dedicated chat page with persistent context
- Render-compatible deployment files

## Architecture

```
FastAPI + Jinja2 templates
├── PostgreSQL (Supabase) — config, snapshots, version log, conversations
├── pydantic-settings — bootstrap env vars (DB URL, API keys)
├── Binance REST API — signed account balance fetch
├── DEGIRO CSV upload + parser
├── Currency converter — exchangerate.host
└── GenAI service — Google / OpenAI / Anthropic
```

## Security

- API keys are never hardcoded. Configure through environment variables using `.env` locally or Render environment variables in production.
- The local `.env` file is excluded from source control via `.gitignore`.
- Database connection strings use `repr=False` in settings to avoid accidental log leakage.
- Use read-only Binance API keys. Do not enable withdrawals for any key used by this app.

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env and set DATABASE_URL or SUPABASE_DB_URL
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Configuration

### Bootstrap environment variables (required)

These are the only values that must come from environment variables. Everything else is stored in the database and editable via the `/config` page.

> **Environment variable priority:** Render environment variables always take priority over `.env` file values. The app only loads `.env` when the file exists locally; on Render (where `.env` is excluded by `.gitignore`), only environment variables are used.

- `DATABASE_URL` or `SUPABASE_DB_URL`: PostgreSQL connection string ( Supabase DB URL takes priority)
- `APP_SECRET_KEY`: FastAPI session/CSRF secret
- `BINANCE_API_KEY` / `BINANCE_API_SECRET`
- `GOOGLE_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`

### Runtime configuration (database-backed)

Once the database is connected, all other settings are managed at `/config`:

- Investor profile, objectives, risk tolerance, horizon
- GenAI provider and model
- Custom prompts for asset insights, macro analysis, portfolio insights, asset comparison, and chat extra context
- Default display currency
- Exchange rate host URL

## Database setup

This project uses Supabase auto-deploy via Git push. Migrations are in `supabase/migrations/`.

1. Connect your Supabase project to this GitHub repository.
2. Push the migration file `supabase/migrations/20260527000000_mvp_05_database_introduced.sql`.
3. Supabase will deploy the schema automatically.
4. Set `SUPABASE_DB_URL` in your `.env` or Render dashboard.

For local PostgreSQL, create the schema manually from the migration file and set `DATABASE_URL`.

## DEGIRO CSV imports

Upload DEGIRO reports from the dashboard. The parser accepts common English/Dutch-style columns and semicolon, comma, or tab delimiters.

For portfolio overview, useful columns include:

- `Product`, `Name`, or `Description`
- `Symbol` or `ISIN`
- `Quantity`, `Number`, or `Amount`
- `Value`, `Market Value`, `Value in EUR`, or `Total`
- `Currency` or `Valuta`
- `Type`, `Product Type`, or `Category`

For account statements, useful columns include:

- `Currency` or `Valuta`
- `Balance`, `Amount`, `Change`, or `Mutatie`

If your DEGIRO export uses different column names, provide a sample CSV and the parser can be adapted.

## Render deployment

This repo includes `render.yaml`, `runtime.txt`, and a production start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

On Render:

1. Create a new Web Service from this repository.
2. Use the included `render.yaml` or set:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Add environment variables in Render dashboard (minimum: `SUPABASE_DB_URL`, `APP_SECRET_KEY`, `BINANCE_API_KEY`, `BINANCE_API_SECRET`).
4. Deploy.

## Version log

- MVP v0.5 database introduced
- MVP v0.3.4 Automated GenAI insights and persistent portfolio chat
- MVP v0.3.3 Env vars adjustments
- MVP v0.3.2 UX improvements
- MVP v0.3.1 Code corrections
- MVP v0.3 added version log
- MVP v0.2 extending the draft
- MVP v0.1 MVP initial draft

Future changes should update the version log with a concise executive entry.

## Notes

This app provides educational analysis only. GenAI output is not financial advice and should be reviewed critically.
