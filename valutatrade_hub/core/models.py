from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Dict

from .exceptions import InsufficientFundsError


def _validate_non_empty_str(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} не может быть пустым")
    return value.strip()


def _validate_password(password: str) -> str:
    password = _validate_non_empty_str(password, "Пароль")
    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")
    return password


def _hash_password(password: str, salt: str) -> str:
    payload = (password + salt).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class User:
    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ) -> None:
        self._user_id = int(user_id)
        self.username = username
        self._hashed_password = _validate_non_empty_str(
            hashed_password,
            "hashed_password",
        )
        self._salt = _validate_non_empty_str(salt, "salt")
        if not isinstance(registration_date, datetime):
            raise TypeError("registration_date должен быть datetime")
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        self._username = _validate_non_empty_str(value, "Имя пользователя")

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    def get_user_info(self) -> dict:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def verify_password(self, password: str) -> bool:
        password = _validate_password(password)
        return _hash_password(password, self._salt) == self._hashed_password

    def change_password(self, new_password: str) -> None:
        new_password = _validate_password(new_password)
        self._hashed_password = _hash_password(new_password, self._salt)


class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        self._currency_code = _validate_non_empty_str(
            currency_code,
            "currency_code",
        ).upper()
        self.balance = balance

    @property
    def currency_code(self) -> str:
        return self._currency_code

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if not isinstance(value, (int, float)):
            raise TypeError("balance должен быть числом")
        value = float(value)
        if value < 0:
            raise ValueError("balance не может быть отрицательным")
        self._balance = value

    def deposit(self, amount: float) -> None:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        self.balance = self.balance + amount

    def withdraw(self, amount: float) -> None:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        if amount > self.balance:
            raise InsufficientFundsError(
                available=self.balance,
                required=amount,
                code=self.currency_code,
            )
        self.balance = self.balance - amount


class Portfolio:
    def __init__(self, user_id: int, wallets: Dict[str, Wallet] | None = None) -> None:
        # Портфель хранит кошельки пользователя
        self._user_id = int(user_id)
        self._wallets: Dict[str, Wallet] = wallets or {}

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def wallets(self) -> Dict[str, Wallet]:
        # Отдаём копию, чтобы не ломали исходник
        return dict(self._wallets)

    def add_currency(self, currency_code: str) -> Wallet:
        # Создаём кошелёк, если его нет
        code = _validate_non_empty_str(currency_code, "currency_code").upper()
        if code in self._wallets:
            raise ValueError(f"Кошелёк '{code}' уже существует")
        wallet = Wallet(currency_code=code, balance=0.0)
        self._wallets[code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet | None:
        # Получаем кошелёк по коду валюты
        code = _validate_non_empty_str(currency_code, "currency_code").upper()
        return self._wallets.get(code)

    def get_total_value(
        self,
        base_currency: str = "USD",
        exchange_rates: dict[str, float] | None = None,
    ) -> float:
        # Считаем итоговую стоимость в base
        base = _validate_non_empty_str(base_currency, "base_currency").upper()
        rates = exchange_rates or {}

        total = 0.0
        for code, wallet in self._wallets.items():
            if code == base:
                total += wallet.balance
                continue

            pair = f"{code}_{base}"
            rate = rates.get(pair)
            if rate is None:
                raise ValueError(f"Не удалось получить курс для {code}→{base}")
            total += wallet.balance * float(rate)

        return total
