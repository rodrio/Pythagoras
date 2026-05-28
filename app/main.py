import logging
import traceback
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.currency import CurrencyConverter
from app.database import Database
from app.errors import AppError, describe_exception
from app.genai import GenAIService
from app.portfolio import PortfolioService
from app.providers import BinanceProvider, DegiroCsvProvider
from app.runtime_config import RuntimeConfig
from app.settings import get_settings

logger = logging.getLogger("pythagoras")
logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

app = FastAPI(title="Pythagoras Portfolio Manager")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.exception_handler(Exception)
async def app_exception_handler(request: Request, exc: Exception):
    message = describe_exception(exc)
    logger.error("Request to %s failed: %s", request.url.path, message)
    logger.error("Traceback:\n%s", "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    try:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"error_message": message},
            status_code=500,
        )
    except Exception as render_exc:
        logger.error("Error template failed to render: %s", render_exc)
        return PlainTextResponse(f"Pythagoras error: {message}", status_code=500)


def database() -> Database:
    settings = get_settings()
    db = Database(settings)
    db.ensure_seed_data()
    return db


def runtime_settings(db: Database | None = None) -> RuntimeConfig:
    settings = get_settings()
    db = db or Database(settings)
    return RuntimeConfig(settings, db.config())


def services() -> tuple[PortfolioService, DegiroCsvProvider, GenAIService, Database, RuntimeConfig]:
    db = database()
    settings = runtime_settings(db)
    degiro = DegiroCsvProvider(DATA_DIR)
    portfolio = PortfolioService(BinanceProvider(settings), degiro, CurrencyConverter(settings), db)
    return portfolio, degiro, GenAIService(settings, db), db, settings


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, currency: str | None = None):
    portfolio, _, genai, db, settings = services()
    display_currency = currency or settings.default_display_currency
    data = await portfolio.dashboard(display_currency)
    try:
        evolution = db.portfolio_evolution()
    except AppError as exc:
        evolution = []
        dashboard_error = exc.user_message
    else:
        dashboard_error = None
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"data": data, "settings": settings, "genai_configured": genai.configured, "evolution": evolution, "error_message": dashboard_error},
    )


@app.get("/version-log", response_class=HTMLResponse)
async def version_log(request: Request):
    return templates.TemplateResponse(request=request, name="version_log.html", context={"entries": database().version_log()})


@app.get("/binance", response_class=HTMLResponse)
async def binance_page(request: Request, currency: str | None = None):
    portfolio, _, _, _, settings = services()
    data = await portfolio.dashboard(currency or settings.default_display_currency)
    holdings = [item for item in data.holdings if item.provider == "Binance"]
    cash = [item for item in data.cash if item.provider == "Binance"]
    return templates.TemplateResponse(request=request, name="binance.html", context={"settings": settings, "holdings": holdings, "cash": cash, "currency": data.display_currency})


@app.post("/binance/update")
async def update_binance():
    portfolio, _, _, _, _ = services()
    await portfolio.refresh_snapshot()
    return RedirectResponse("/binance", status_code=303)


@app.get("/degiro", response_class=HTMLResponse)
async def degiro_page(request: Request):
    files = sorted(DATA_DIR.glob("degiro_*.csv"))
    return templates.TemplateResponse(request=request, name="degiro.html", context={"files": files})


@app.post("/upload/degiro")
async def upload_degiro(report_type: str = Form(...), file: UploadFile = File(...)):
    portfolio, degiro, _, _, _ = services()
    content = await file.read()
    degiro.save_upload(report_type, file.filename or "report.csv", content)
    await portfolio.refresh_snapshot()
    return RedirectResponse("/degiro", status_code=303)


@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request, saved: str | None = None):
    db = database()
    return templates.TemplateResponse(request=request, name="config.html", context={"settings": runtime_settings(db), "rows": db.config_rows(), "saved": saved == "1", "db_configured": db.configured})


@app.post("/config")
async def save_config(request: Request):
    form = await request.form()
    updates = {key: str(value) for key, value in form.items()}
    database().update_config(updates)
    return RedirectResponse("/config?saved=1", status_code=303)


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request, currency: str | None = None):
    portfolio, _, genai, _, settings = services()
    data = await portfolio.dashboard(currency or settings.default_display_currency)
    return templates.TemplateResponse(request=request, name="chat.html", context={"data": data, "settings": settings, "genai_configured": genai.configured, "conversation": genai._conversation_block()})


@app.post("/chat", response_class=HTMLResponse)
async def chat(request: Request, message: str = Form(...), currency: str = Form("EUR")):
    portfolio, _, genai, _, settings = services()
    data = await portfolio.dashboard(currency)
    answer = await genai.chat(data, message)
    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={"data": data, "settings": settings, "genai_configured": genai.configured, "chat_message": message, "chat_answer": answer, "conversation": genai._conversation_block()},
    )


@app.get("/insights/portfolio", response_class=HTMLResponse)
async def portfolio_insight(request: Request, currency: str | None = None):
    portfolio, _, genai, _, settings = services()
    data = await portfolio.dashboard(currency or settings.default_display_currency)
    return templates.TemplateResponse(request=request, name="insight_popup.html", context={"title": "Portfolio insights", "answer": await genai.portfolio_insight(data)})


@app.get("/insights/asset/{symbol}", response_class=HTMLResponse)
async def asset_insight(request: Request, symbol: str, currency: str | None = None):
    portfolio, _, genai, _, settings = services()
    data = await portfolio.dashboard(currency or settings.default_display_currency)
    return templates.TemplateResponse(request=request, name="insight_popup.html", context={"title": f"{symbol} insights", "answer": await genai.asset_insight(data, symbol)})


@app.get("/macro/asset/{symbol}", response_class=HTMLResponse)
async def asset_macro(request: Request, symbol: str, currency: str | None = None):
    portfolio, _, genai, _, settings = services()
    data = await portfolio.dashboard(currency or settings.default_display_currency)
    return templates.TemplateResponse(request=request, name="insight_popup.html", context={"title": f"{symbol} macro context", "answer": await genai.asset_macro(data, symbol)})


@app.get("/compare/asset/{symbol}", response_class=HTMLResponse)
async def asset_compare(request: Request, symbol: str, currency: str | None = None):
    portfolio, _, genai, _, settings = services()
    data = await portfolio.dashboard(currency or settings.default_display_currency)
    return templates.TemplateResponse(request=request, name="compare.html", context={"symbol": symbol, "comparison_html": await genai.asset_compare(data, symbol)})


@app.get("/health")
def health():
    return {"status": "ok"}
