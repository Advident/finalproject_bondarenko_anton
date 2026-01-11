from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParserConfig:
    EXCHANGERATE_API_KEY: str | None = os.getenv("$EXCHANGERATE_API_KEY")

    # URL
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # База
    BASE_FIAT_CURRENCY: str = "USD"

    # Какие валюты тянуть
    FIAT_CURRENCIES: tuple[str, ...] = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple[str, ...] = ("BTC", "ETH", "SOL")

    # Мапа тикер -> coin id
    CRYPTO_ID_MAP: dict[str, str] = None  # type: ignore[assignment]

    # Таймаут
    REQUEST_TIMEOUT: int = 10

    # Пути
    RATES_FILE_PATH: str = "data/rates.json"
    HISTORY_FILE_PATH: str = "data/exchange_rates.json"

    def __post_init__(self) -> None:
        # Дефолт для dict в dataclass
        if self.CRYPTO_ID_MAP is None:
            object.__setattr__(
                self,
                "CRYPTO_ID_MAP",
                {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana"},
            )

    @property
    def rates_path(self) -> Path:
        return Path(self.RATES_FILE_PATH)

    @property
    def history_path(self) -> Path:
        return Path(self.HISTORY_FILE_PATH)
