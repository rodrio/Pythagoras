import os
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.currency import CurrencyConverter
from app.genai import GenAIService
from app.portfolio import PortfolioService
from app.providers import BinanceProvider, DegiroCsvProvider
from app.settings import get_settings

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ENV_FILE = BASE_DIR / ".env"

app = FastAPI(title="Pythagoras Portfolio Manager")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def services() -> tuple[PortfolioService, DegiroCsvProvider, GenAIService]:
    settings = get_settings()
    degiro = DegiroCsvProvider(DATA_DIR)
    portfolio = PortfolioService(BinanceProvider(settings), degiro, CurrencyConverter(settings))
    return portfolio, degiro, GenAIService(settings)


def masked_environment() -> list[dict[str, str]]:
    settings = get_settings()
    sensitive = {"APP_SECRET_KEY", "BINANCE_API_KEY", "BINANCE_API_SECRET", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"}
    names = [
        "APP_ENV",
        "DEFAULT_DISPLAY_CURRENCY",
        "INVESTOR_PROFILE",
        "INVESTMENT_OBJECTIVES",
        "RISK_TOLERANCE",
        "INVESTMENT_HORIZON",
        "BINANCE_API_KEY",
        "BINANCE_API_SECRET",
        "BINANCE_BASE_URL",
        "GENAI_PROVIDER",
        "GENAI_MODEL",
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "EXCHANGERATE_HOST_URL",
    ]
    values = settings.model_dump()
    rows: list[dict[str, str]] = []
    for name in names:
        value = os.getenv(name)
        if value is None:
            value = values.get(name.lower())
        detected = value not in (None, "")
        rows.append({"name": name, "status": "detected" if detected else "missing", "value": "configured" if name in sensitive and detected else str(value or "")})
    return rows


def update_env_file(updates: dict[str, str]) -> None:
    existing = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    updated_keys: set[str] = set()
    lines: list[str] = []
    for line in existing:
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            lines.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in updates:
            lines.append(f"{key}={updates[key]}")
            updated_keys.add(key)
        else:
            lines.append(line)
    for key, value in updates.items():
        if key not in updated_keys:
            lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    get_settings.cache_clear()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, currency: str | None = None):
    settings = get_settings()
    portfolio, _, genai = services()
    display_currency = currency or settings.default_display_currency
    data = await portfolio.dashboard(display_currency)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "data": data, "settings": settings, "genai_configured": genai.configured},
    )


@app.get("/menu", response_class=HTMLResponse)
async def menu(request: Request):
    return templates.TemplateResponse("menu.html", {"request": request})


@app.get("/version-log", response_class=HTMLResponse)
async def version_log(request: Request):
    entries = [
        "MVP v0.1 first deploy",
        "MVP v0.2 added a menu to manage sources and GenAI",
        "MVP v0.3 added executive version log accessible from the menu",
    ]
    return templates.TemplateResponse("version_log.html", {"request": request, "entries": entries})


@app.get("/binance", response_class=HTMLResponse)
async def binance_page(request: Request, currency: str | None = None):
    settings = get_settings()
    portfolio, _, _ = services()
    data = await portfolio.dashboard(currency or settings.default_display_currency)
    holdings = [item for item in data.holdings if item.provider == "Binance"]
    cash = [item for item in data.cash if item.provider == "Binance"]
    return templates.TemplateResponse("binance.html", {"request": request, "settings": settings, "holdings": holdings, "cash": cash, "currency": data.display_currency})


@app.post("/binance/update")
async def update_binance():
    await BinanceProvider(get_settings()).fetch()
    return RedirectResponse("/binance", status_code=303)


@app.get("/degiro", response_class=HTMLResponse)
async def degiro_page(request: Request):
    files = sorted(DATA_DIR.glob("degiro_*.csv"))
    return templates.TemplateResponse("degiro.html", {"request": request, "files": files})


@app.post("/upload/degiro")
async def upload_degiro(report_type: str = Form(...), file: UploadFile = File(...)):
    _, degiro, _ = services()
    content = await file.read()
    degiro.save_upload(report_type, file.filename or "report.csv", content)
    return RedirectResponse("/degiro", status_code=303)


@app.get("/environment", response_class=HTMLResponse)
async def environment_page(request: Request):
    return templates.TemplateResponse("environment.html", {"request": request, "variables": masked_environment()})


@app.get("/config/genai", response_class=HTMLResponse)
async def genai_config_page(request: Request, saved: str | None = None):
    return templates.TemplateResponse("genai_config.html", {"request": request, "settings": get_settings(), "saved": saved == "1"})


@app.post("/config/genai")
async def save_genai_config(provider: str = Form(...), model: str = Form("")):
    if provider not in {"disabled", "google", "openai", "anthropic"}:
        provider = "disabled"
    update_env_file({"GENAI_PROVIDER": provider, "GENAI_MODEL": model.strip()})
    return RedirectResponse("/config/genai?saved=1", status_code=303)


@app.post("/chat", response_class=HTMLResponse)
async def chat(request: Request, message: str = Form(...), currency: str = Form("EUR")):
    portfolio, _, genai = services()
    data = await portfolio.dashboard(currency)
    answer = await genai.chat(data, message)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "data": data, "settings": get_settings(), "genai_configured": genai.configured, "chat_message": message, "chat_answer": answer},
    )


@app.post("/insights", response_class=HTMLResponse)
async def insights(request: Request, currency: str = Form("EUR")):
    portfolio, _, genai = services()
    data = await portfolio.dashboard(currency)
    answer = await genai.insights(data)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "data": data, "settings": get_settings(), "genai_configured": genai.configured, "chat_message": "Generate portfolio insights", "chat_answer": answer},
    )


@app.get("/health")
def health():
    return {"status": "ok"}
