# Pythagoras Portfolio Manager

A Python FastAPI investment dashboard for viewing Shares, Funds, Cryptos, cash balances, provider totals, currency views, Binance balances, DEGIRO CSV imports, and GenAI portfolio chat.

## Features

- Central dashboard with three sections: Shares, Funds, Cryptos
- Holdings and cash totals overall and by provider
- Currency display as native, EUR, or USD
- Binance account balance integration using signed REST API calls
- DEGIRO CSV import for:
  - Portfolio overview
  - Account statement
  - Transaction statement upload storage
- GenAI integration with selectable provider:
  - Google Gemini
  - OpenAI
  - Anthropic
- Portfolio chat and generated insights with investor profile context and guardrails
- Render-compatible deployment files

## Security

API keys are never hardcoded in the app. Configure them through environment variables using `.env` locally or Render environment variables in production.

Use read-only Binance API keys. Do not enable withdrawals for any key used by this app.

The API keys included in the original request should be rotated if they are real secrets, because chat transcripts and source control are not secure secret stores.

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Configuration

Edit `.env` locally or set these values in Render:

- `BINANCE_API_KEY`
- `BINANCE_API_SECRET`
- `GENAI_PROVIDER`: `disabled`, `google`, `openai`, or `anthropic`
- `GENAI_MODEL`: optional model override
- `GOOGLE_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `INVESTOR_PROFILE`
- `INVESTMENT_OBJECTIVES`
- `RISK_TOLERANCE`
- `INVESTMENT_HORIZON`
- `DEFAULT_DISPLAY_CURRENCY`: `NATIVE`, `EUR`, or `USD`

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
3. Add environment variables in Render dashboard.
4. Deploy.

## Version log

- MVP v0.1 first deploy
- MVP v0.2 added a menu to manage sources and GenAI
- MVP v0.3 added executive version log accessible from the menu
- MVP v0.4 fixed local loading and template compatibility
- MVP v0.5 refined environment visibility, GenAI model suggestions, and dashboard layout

Future changes should update the version log with a concise executive entry.

## Notes

This app provides educational analysis only. GenAI output is not financial advice and should be reviewed critically.
