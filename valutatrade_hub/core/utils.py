from __future__ import annotations

import json
from datetime import datetime
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
    # Текущее время ISO
    return datetime.now().isoformat(timespec="seconds")


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
    # Парсим ISO
    return datetime.fromisoformat(dt_str)


def is_rate_fresh(updated_at_iso: str, ttl_seconds: int) -> bool:
    # Проверка TTL
    dt = parse_iso(updated_at_iso)
    age = (datetime.now() - dt).total_seconds()
    return age <= ttl_seconds


def make_pair(from_code: str, to_code: str) -> str:
    # Ключ пары валют
    return f"{from_code}_{to_code}"
