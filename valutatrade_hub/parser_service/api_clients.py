from __future__ import annotations

from abc import ABC, abstractmethod
from time import perf_counter
from typing import Any

import requests

from ..core.exceptions import ApiRequestError


class BaseApiClient(ABC):
    # Единый интерфейс клиента
    @abstractmethod
    def fetch_rates(self) -> tuple[dict[str, float], dict[str, Any]]:
        """
        Возвращает:
        - rates: {"BTC_USD": 59337.21, ...}
        - meta: мета-инфа по запросу (source, request_ms, status_code, etag, raw)
        """
        raise NotImplementedError


class CoinGeckoClient(BaseApiClient):
    def __init__(
        self,
        base_url: str,
        crypto_id_map: dict[str, str],
        timeout: int = 10,
    ) -> None:
        self._base_url = base_url
        self._crypto_id_map = crypto_id_map
        self._timeout = timeout

    def fetch_rates(self) -> tuple[dict[str, float], dict[str, Any]]:
        # Формируем ids
        ids = ",".join(self._crypto_id_map.values())
        params = {"ids": ids, "vs_currencies": "usd"}

        t0 = perf_counter()
        try:
            resp = requests.get(self._base_url, params=params, timeout=self._timeout)
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"CoinGecko: {e}") from e
        ms = int((perf_counter() - t0) * 1000)

        if resp.status_code != 200:
            raise ApiRequestError(f"CoinGecko: status_code={resp.status_code}")

        try:
            data = resp.json()
        except ValueError as e:
            raise ApiRequestError("CoinGecko: invalid JSON") from e

        # Приводим к {"BTC_USD": rate}
        rates: dict[str, float] = {}
        for code, coin_id in self._crypto_id_map.items():
            if coin_id in data and "usd" in data[coin_id]:
                rates[f"{code}_USD"] = float(data[coin_id]["usd"])

        meta = {
            "source": "CoinGecko",
            "request_ms": ms,
            "status_code": resp.status_code,
            "etag": resp.headers.get("ETag"),
            "raw": {"ids": ids, "vs": "usd"},
        }
        return rates, meta


class ExchangeRateApiClient(BaseApiClient):
    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        base_currency: str,
        timeout: int = 10,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._base_currency = base_currency
        self._timeout = timeout

    def fetch_rates(self) -> tuple[dict[str, float], dict[str, Any]]:
        if not self._api_key:
            raise ApiRequestError(
                "ExchangeRate-API: не задан ключ EXCHANGERATE_API_KEY"
            )

        url = f"{self._base_url}/{self._api_key}/latest/{self._base_currency}"

        t0 = perf_counter()
        try:
            resp = requests.get(url, timeout=self._timeout)
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"ExchangeRate-API: {e}") from e
        ms = int((perf_counter() - t0) * 1000)

        if resp.status_code != 200:
            # Частый кейс: 429 (лимит) или 403 (ключ)
            raise ApiRequestError(f"ExchangeRate-API: status_code={resp.status_code}")

        try:
            data = resp.json()
        except ValueError as e:
            raise ApiRequestError("ExchangeRate-API: invalid JSON") from e

        if data.get("result") != "success":
            raise ApiRequestError(f"ExchangeRate-API: result={data.get('result')}")

        # В ответе rates: {"EUR": 0.927, ...} при base_code=USD
        raw_rates = data.get("rates", {})
        rates: dict[str, float] = {}
        for to_code, val in raw_rates.items():
            try:
                rates[f"{to_code}_USD"] = float(val)
            except (TypeError, ValueError):
                continue

        meta = {
            "source": "ExchangeRate-API",
            "request_ms": ms,
            "status_code": resp.status_code,
            "etag": resp.headers.get("ETag"),
            "raw": {"base": self._base_currency},
            "time_last_update_utc": data.get("time_last_update_utc"),
        }
        return rates, meta
