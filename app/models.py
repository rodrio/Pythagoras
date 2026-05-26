from enum import StrEnum
from pydantic import BaseModel, Field


class AssetSection(StrEnum):
    shares = "Shares"
    funds = "Funds"
    cryptos = "Cryptos"


class Holding(BaseModel):
    provider: str
    section: AssetSection
    symbol: str
    name: str
    quantity: float
    currency: str
    market_value: float
    cost_basis: float | None = None

    @property
    def unrealized_pnl(self) -> float | None:
        if self.cost_basis is None:
            return None
        return self.market_value - self.cost_basis


class CashBalance(BaseModel):
    provider: str
    currency: str
    amount: float


class PortfolioSnapshot(BaseModel):
    holdings: list[Holding] = Field(default_factory=list)
    cash: list[CashBalance] = Field(default_factory=list)


class ConvertedHolding(Holding):
    display_currency: str
    display_market_value: float
    display_cost_basis: float | None = None


class ConvertedCash(CashBalance):
    display_currency: str
    display_amount: float


class DashboardData(BaseModel):
    display_currency: str
    total_holdings_value: float
    total_cash_value: float
    holdings: list[ConvertedHolding]
    cash: list[ConvertedCash]
    by_section: dict[str, float]
    by_provider: dict[str, float]
