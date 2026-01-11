from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .exceptions import CurrencyNotFoundError


def _validate_code(code: str) -> str:
    # Код: 2–5 символов, верхний регистр
    if not isinstance(code, str) or not code.strip():
        raise ValueError("code — непустая строка")
    code = code.strip().upper()
    if not (2 <= len(code) <= 5) or " " in code:
        raise ValueError("code должен быть 2–5 символов без пробелов")
    return code


def _validate_name(name: str) -> str:
    # Имя: непустая строка
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name — непустая строка")
    return name.strip()


@dataclass(frozen=True)
class Currency(ABC):
    # Базовая валюта
    name: str
    code: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _validate_name(self.name))
        object.__setattr__(self, "code", _validate_code(self.code))

    @abstractmethod
    def get_display_info(self) -> str:
        # Строка для UI/логов
        raise NotImplementedError


@dataclass(frozen=True)
class FiatCurrency(Currency):
    issuing_country: str

    def __post_init__(self) -> None:
        super().__post_init__()
        if (
            not isinstance(self.issuing_country, str)
            or not self.issuing_country.strip()
        ):
            raise ValueError("issuing_country — непустая строка")
        object.__setattr__(self, "issuing_country", self.issuing_country.strip())

    def get_display_info(self) -> str:
        return (
            f"[FIAT] {self.code} — {self.name} "
            f"(Issuing: {self.issuing_country})"
        )


@dataclass(frozen=True)
class CryptoCurrency(Currency):
    algorithm: str
    market_cap: float

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.algorithm, str) or not self.algorithm.strip():
            raise ValueError("algorithm — непустая строка")
        object.__setattr__(self, "algorithm", self.algorithm.strip())

        if not isinstance(self.market_cap, (int, float)) or float(self.market_cap) < 0:
            raise ValueError("market_cap должен быть >= 0")
        object.__setattr__(self, "market_cap", float(self.market_cap))

    def get_display_info(self) -> str:
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"
        )


# Мини-реестр валют
_REGISTRY: dict[str, Currency] = {
    "USD": FiatCurrency(
        name="US Dollar",
        code="USD",
        issuing_country="United States",
    ),
    "EUR": FiatCurrency(
        name="Euro",
        code="EUR",
        issuing_country="Eurozone",
    ),
    "RUB": FiatCurrency(
        name="Russian Ruble",
        code="RUB",
        issuing_country="Russia",
    ),
    "BTC": CryptoCurrency(
        name="Bitcoin",
        code="BTC",
        algorithm="SHA-256",
        market_cap=1.12e12,
    ),
    "ETH": CryptoCurrency(
        name="Ethereum",
        code="ETH",
        algorithm="Ethash",
        market_cap=4.50e11,
    ),
}


def get_currency(code: str) -> Currency:
    # Фабрика валют по коду
    if not isinstance(code, str):
        raise CurrencyNotFoundError(str(code))
    c = code.strip().upper()
    cur = _REGISTRY.get(c)
    if cur is None:
        raise CurrencyNotFoundError(c)
    return cur


def supported_codes() -> list[str]:
    # Список поддерживаемых кодов
    return sorted(_REGISTRY.keys())
