from app.currency import CurrencyConverter
from app.models import ConvertedCash, ConvertedHolding, DashboardData, PortfolioSnapshot
from app.providers import BinanceProvider, DegiroCsvProvider
from app.database import Database


class PortfolioService:
    def __init__(self, binance: BinanceProvider, degiro: DegiroCsvProvider, converter: CurrencyConverter, database: Database | None = None):
        self.binance = binance
        self.degiro = degiro
        self.converter = converter
        self.database = database

    async def snapshot(self) -> PortfolioSnapshot:
        if self.database:
            stored = self.database.latest_snapshot()
            if stored:
                return stored
        return await self.refresh_snapshot()

    async def refresh_snapshot(self) -> PortfolioSnapshot:
        binance = await self.binance.fetch()
        degiro = self.degiro.fetch()
        if self.database:
            self.database.save_snapshot("Binance", "api", binance)
            self.database.save_snapshot("DEGIRO", "csv", degiro)
        return PortfolioSnapshot(holdings=[*binance.holdings, *degiro.holdings], cash=[*binance.cash, *degiro.cash])

    async def dashboard(self, display_currency: str) -> DashboardData:
        snapshot = await self.snapshot()
        holdings: list[ConvertedHolding] = []
        cash: list[ConvertedCash] = []
        for item in snapshot.holdings:
            target = item.currency if display_currency == "NATIVE" else display_currency
            display_market_value = await self.converter.convert(item.market_value, item.currency, target)
            display_cost_basis = None if item.cost_basis is None else await self.converter.convert(item.cost_basis, item.currency, target)
            holdings.append(ConvertedHolding(**item.model_dump(), display_currency=target, display_market_value=display_market_value, display_cost_basis=display_cost_basis))
        for item in snapshot.cash:
            target = item.currency if display_currency == "NATIVE" else display_currency
            cash.append(ConvertedCash(**item.model_dump(), display_currency=target, display_amount=await self.converter.convert(item.amount, item.currency, target)))
        by_section: dict[str, float] = {}
        by_provider: dict[str, float] = {}
        for item in holdings:
            by_section[item.section.value] = round(by_section.get(item.section.value, 0) + item.display_market_value, 2)
            by_provider[item.provider] = round(by_provider.get(item.provider, 0) + item.display_market_value, 2)
        for item in cash:
            by_provider[item.provider] = round(by_provider.get(item.provider, 0) + item.display_amount, 2)
        return DashboardData(
            display_currency=display_currency,
            total_holdings_value=round(sum(item.display_market_value for item in holdings), 2),
            total_cash_value=round(sum(item.display_amount for item in cash), 2),
            holdings=holdings,
            cash=cash,
            by_section=by_section,
            by_provider=by_provider,
        )
