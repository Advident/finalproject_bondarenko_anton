from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .currencies import get_currency
from .exceptions import CurrencyNotFoundError

# Папка с JSON-данными
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
USERS_PATH = DATA_DIR / "users.json"
PORTFOLIOS_PATH = DATA_DIR / "portfolios.json"
RATES_PATH = DATA_DIR / "rates.json"


def ensure_data_files() -> None:
    # Создаём data/ и дефолтные JSON
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _ensure(path: Path, default_text: str) -> None:
        if not path.exists():
            path.write_text(default_text, encoding="utf-8")
            return
        if path.read_text(encoding="utf-8").strip() == "":
            path.write_text(default_text, encoding="utf-8")

    _ensure(USERS_PATH, "[]")
    _ensure(PORTFOLIOS_PATH, "[]")
    _ensure(RATES_PATH, '{"pairs": {}, "last_refresh": null}')


def load_json(path: Path):
    # Читаем JSON
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    # Пишем JSON
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def now_iso() -> str:
    # Текущее время в UTC (ISO + Z)
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

def validate_currency_code(code: str) -> str:
    # Проверяем через реестр валют
    try:
        cur = get_currency(code)
    except CurrencyNotFoundError:
        raise
    return cur.code


def validate_amount(amount) -> float:
    # Сумма: float > 0
    try:
        x = float(amount)
    except (TypeError, ValueError) as err:
        raise ValueError("'amount' должен быть положительным числом") from err

    if x <= 0:
        raise ValueError("'amount' должен быть положительным числом")

    return x


def parse_iso(dt_str: str) -> datetime:
    # Парсим ISO, поддерживаем суффикс Z (UTC)
    s = str(dt_str).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    dt = datetime.fromisoformat(s)

    # Если пришло naive-время — считаем его UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def is_rate_fresh(updated_at_iso: str, ttl_seconds: int) -> bool:
    # Проверка TTL (в UTC)
    dt = parse_iso(updated_at_iso)
    age = (datetime.now(timezone.utc) - dt).total_seconds()
    return age <= ttl_seconds


def make_pair(from_code: str, to_code: str) -> str:
    # Ключ пары валют
    return f"{from_code}_{to_code}"
