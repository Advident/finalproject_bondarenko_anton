from __future__ import annotations

import secrets
from datetime import datetime

from ..decorators import log_action
from ..infra.database import DatabaseManager
from ..infra.settings import SettingsLoader
from .exceptions import ApiRequestError
from .models import Wallet, _hash_password
from .utils import is_rate_fresh, make_pair, validate_amount, validate_currency_code

# Сессия в памяти
_current_user_id: int | None = None
_current_username: str | None = None

_db = DatabaseManager()
_settings = SettingsLoader()


def _next_user_id(users: list[dict]) -> int:
    if not users:
        return 1
    return max(int(u["user_id"]) for u in users) + 1


def _find_user_by_username(users: list[dict], username: str) -> dict | None:
    for u in users:
        if u.get("username") == username:
            return u
    return None


def _load_portfolio(user_id: int) -> dict | None:
    portfolios = _db.read(_db.portfolios_path)
    for p in portfolios:
        if int(p.get("user_id")) == int(user_id):
            return p
    return None


def _save_portfolio(user_id: int, wallets: dict) -> None:
    portfolios = _db.read(_db.portfolios_path)
    for p in portfolios:
        if int(p.get("user_id")) == int(user_id):
            p["wallets"] = wallets
            _db.write(_db.portfolios_path, portfolios)
            return
    portfolios.append({"user_id": user_id, "wallets": wallets})
    _db.write(_db.portfolios_path, portfolios)


@log_action("REGISTER")
def register(username: str, password: str) -> str:
    username = username.strip()
    if not username:
        raise ValueError("Имя пользователя не может быть пустым")
    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    users = _db.read(_db.users_path)
    if _find_user_by_username(users, username) is not None:
        raise ValueError(f"Имя пользователя '{username}' уже занято")

    user_id = _next_user_id(users)
    salt = secrets.token_hex(4)
    hashed = _hash_password(password, salt)

    users.append(
        {
            "user_id": user_id,
            "username": username,
            "hashed_password": hashed,
            "salt": salt,
            "registration_date": datetime.now().isoformat(timespec="seconds"),
        }
    )
    _db.write(_db.users_path, users)

    _save_portfolio(user_id, wallets={})

    return (
        f"Пользователь '{username}' зарегистрирован (id={user_id}). "
        f"Войдите: login --username {username} --password ****"
    )


@log_action("LOGIN")
def login(username: str, password: str) -> str:
    users = _db.read(_db.users_path)
    user = _find_user_by_username(users, username)
    if user is None:
        raise ValueError(f"Пользователь '{username}' не найден")

    given = _hash_password(password, user["salt"])
    if given != user["hashed_password"]:
        raise ValueError("Неверный пароль")

    global _current_user_id, _current_username
    _current_user_id = int(user["user_id"])
    _current_username = username

    return f"Вы вошли как '{username}'"


def require_login() -> None:
    if _current_user_id is None:
        raise PermissionError("Сначала выполните login")


def _stub_fetch_rate(pair: str) -> float:
    # Заглушка вместо Parser Service
    stub = {
        "EUR_USD": 1.08,
        "BTC_USD": 59000.0,
        "ETH_USD": 3700.0,
        "RUB_USD": 0.010,
        "USD_BTC": 1 / 59000.0,
        "USD_EUR": 1 / 1.08,
    }
    rate = stub.get(pair)
    if rate is None:
        raise ApiRequestError(f"нет данных для пары {pair}")
    return float(rate)


def get_rate(from_code: str, to_code: str) -> dict:
    # Валидация через реестр валют
    f = validate_currency_code(from_code)
    t = validate_currency_code(to_code)

    ttl = int(_settings.get("RATES_TTL_SECONDS", 300))
    key = make_pair(f, t)

    data = _db.read(_db.rates_path)
    pairs = data.get("pairs", {}) if isinstance(data, dict) else {}
    entry = pairs.get(key) if isinstance(pairs, dict) else None

    # Есть запись в кеше
    if isinstance(entry, dict) and "rate" in entry and "updated_at" in entry:
        if is_rate_fresh(entry["updated_at"], ttl):
            return {
                "from": f,
                "to": t,
                "rate": float(entry["rate"]),
                "updated_at": entry["updated_at"],
                "source": entry.get("source"),
            }
        # Просрочено — честно сообщаем
        raise ApiRequestError("Данные в кеше устарели. Выполните 'update-rates'.")

    # Нет записи
    raise ApiRequestError(f"Курс {f}→{t} недоступен. Выполните 'update-rates'.")


@log_action("BUY", verbose=True)
def buy(currency_code: str, amount, base: str = "USD") -> dict:
    require_login()

    code = validate_currency_code(currency_code)  # CurrencyNotFoundError
    amt = validate_amount(amount)
    base = validate_currency_code(base)

    raw = _load_portfolio(_current_user_id) or {
        "user_id": _current_user_id,
        "wallets": {},
    }
    wallets = raw["wallets"]

    if code not in wallets:
        wallets[code] = {"balance": 0.0}

    before = float(wallets[code]["balance"])
    w = Wallet(currency_code=code, balance=before)
    w.deposit(amt)
    after = w.balance
    wallets[code]["balance"] = after

    _save_portfolio(_current_user_id, wallets)

    # Оценка стоимости
    rate_info = get_rate(code, base)
    est = amt * rate_info["rate"]

    return {
        "currency": code,
        "amount": amt,
        "base": base,
        "rate": rate_info["rate"],
        "estimated_cost": est,
        "verbose": f"{code}: было {before:.4f} → стало {after:.4f}",
    }


@log_action("SELL", verbose=True)
def sell(currency_code: str, amount, base: str = "USD") -> dict:
    require_login()

    code = validate_currency_code(currency_code)
    amt = validate_amount(amount)
    base = validate_currency_code(base)

    raw = _load_portfolio(_current_user_id)
    if raw is None or not raw.get("wallets") or code not in raw["wallets"]:
        raise ValueError(
            f"У вас нет кошелька '{code}'. "
            "Добавьте валюту: она создаётся автоматически "
            "при первой покупке."
        )

    wallets = raw["wallets"]
    before = float(wallets[code]["balance"])

    w = Wallet(currency_code=code, balance=before)
    w.withdraw(amt)  # может бросить InsufficientFundsError
    after = w.balance
    wallets[code]["balance"] = after

    _save_portfolio(_current_user_id, wallets)

    # Оценка выручки
    rate_info = get_rate(code, base)
    est = amt * rate_info["rate"]

    return {
        "currency": code,
        "amount": amt,
        "base": base,
        "rate": rate_info["rate"],
        "estimated_revenue": est,
        "verbose": f"{code}: было {before:.4f} → стало {after:.4f}",
    }


def show_portfolio(base: str = "USD") -> dict:
    require_login()
    base = validate_currency_code(base)

    raw = _load_portfolio(_current_user_id)
    if raw is None or not raw.get("wallets"):
        return {
            "username": _current_username,
            "base": base,
            "rows": [],
            "total": 0.0,
        }

    wallets = raw["wallets"]
    rows = []
    total = 0.0

    for code, payload in wallets.items():
        code = validate_currency_code(code)
        bal = float(payload.get("balance", 0.0))

        if code == base:
            value_base = bal
        else:
            rate = get_rate(code, base)["rate"]
            value_base = bal * rate

        rows.append((code, bal, value_base))
        total += value_base

    return {"username": _current_username, "base": base, "rows": rows, "total": total}
