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

app = FastAPI(title="Pythagoras Portfolio Manager")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def services() -> tuple[PortfolioService, DegiroCsvProvider, GenAIService]:
    settings = get_settings()
    degiro = DegiroCsvProvider(DATA_DIR)
    portfolio = PortfolioService(BinanceProvider(settings), degiro, CurrencyConverter(settings))
    return portfolio, degiro, GenAIService(settings)


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


@app.post("/upload/degiro")
async def upload_degiro(report_type: str = Form(...), file: UploadFile = File(...)):
    _, degiro, _ = services()
    content = await file.read()
    degiro.save_upload(report_type, file.filename or "report.csv", content)
    return RedirectResponse("/", status_code=303)


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
