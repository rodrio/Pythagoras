import httpx

from app.settings import Settings


class CurrencyConverter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._cache: dict[tuple[str, str], float] = {}

    async def rate(self, source: str, target: str) -> float:
        source = source.upper()
        target = target.upper()
        if source == target or target == "NATIVE":
            return 1.0
        key = (source, target)
        if key in self._cache:
            return self._cache[key]
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(
                    f"{self.settings.exchangerate_host_url.rstrip('/')}/convert",
                    params={"from": source, "to": target, "amount": 1},
                )
                response.raise_for_status()
                data = response.json()
                value = float(data.get("result") or data.get("info", {}).get("rate") or 1.0)
        except Exception:
            value = 1.0
        self._cache[key] = value
        return value

    async def convert(self, amount: float, source: str, target: str) -> float:
        return round(amount * await self.rate(source, target), 2)
