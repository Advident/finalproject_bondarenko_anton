from __future__ import annotations

import shlex

from prettytable import PrettyTable

from ..core import usecases
from ..core.currencies import supported_codes
from ..core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from ..infra.settings import SettingsLoader
from ..logging_config import setup_logging
from ..parser_service.api_clients import CoinGeckoClient, ExchangeRateApiClient
from ..parser_service.config import ParserConfig
from ..parser_service.storage import RatesStorage
from ..parser_service.updater import RatesUpdater


def _parse_args(tokens: list[str]) -> dict[str, str]:
    # Парсинг --key value
    args: dict[str, str] = {}
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.startswith("--"):
            key = t[2:]
            if i + 1 >= len(tokens):
                raise ValueError(f"Не задано значение для {t}")
            args[key] = tokens[i + 1]
            i += 2
        else:
            i += 1
    return args


def _print_portfolio(data: dict) -> None:
    # Печать портфеля таблицей
    username = data["username"]
    base = data["base"]
    rows = data.get("rows", [])
    total = data.get("total", 0.0)

    if not rows:
        print(f"Портфель пользователя '{username}' пуст.")
        return

    table = PrettyTable()
    table.field_names = ["Currency", "Balance", f"Value ({base})"]
    for code, bal, val in rows:
        table.add_row([code, f"{bal:.4f}", f"{val:,.2f}"])

    print(f"Портфель пользователя '{username}' (база: {base}):")
    print(table)
    print("-" * 45)
    print(f"ИТОГО: {total:,.2f} {base}")


def _print_help() -> None:
    # Подсказка
    print(
        "ValutaTrade Hub CLI. Команды: "
        "register/login/show-portfolio/buy/sell/get-rate/"
        "update-rates/show-rates, exit."
    )


def main() -> None:
    # Настраиваем логи
    settings = SettingsLoader()
    setup_logging(
        log_path=settings.get("LOG_PATH"),
        level=settings.get("LOG_LEVEL", "INFO"),
    )

    _print_help()

    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            return

        if not raw:
            continue
        if raw in {"exit", "quit"}:
            print("Выход.")
            return

        try:
            tokens = shlex.split(raw)
            cmd = tokens[0]
            args = _parse_args(tokens[1:])

            if cmd == "register":
                msg = usecases.register(
                    username=args.get("username", ""),
                    password=args.get("password", ""),
                )
                print(msg)

            elif cmd == "login":
                msg = usecases.login(
                    username=args.get("username", ""),
                    password=args.get("password", ""),
                )
                print(msg)

            elif cmd == "show-portfolio":
                base = args.get("base", "USD")
                data = usecases.show_portfolio(base=base)
                _print_portfolio(data)

            elif cmd == "buy":
                res = usecases.buy(
                    currency_code=args.get("currency", ""),
                    amount=args.get("amount"),
                    base=args.get("base", "USD"),
                )
                print(
                    f"Покупка выполнена: {res['amount']:.4f} {res['currency']} "
                    f"по курсу {res['rate']:.6f} {res['base']}/{res['currency']}"
                )
                print(
                    "Оценочная стоимость покупки: "
                    f"{res['estimated_cost']:,.2f} {res['base']}"
                )

            elif cmd == "sell":
                res = usecases.sell(
                    currency_code=args.get("currency", ""),
                    amount=args.get("amount"),
                    base=args.get("base", "USD"),
                )
                print(
                    f"Продажа выполнена: {res['amount']:.4f} {res['currency']} "
                    f"по курсу {res['rate']:.6f} {res['base']}/{res['currency']}"
                )
                print(
                    "Оценочная выручка: "
                    f"{res['estimated_revenue']:,.2f} {res['base']}"
                )

            elif cmd == "get-rate":
                res = usecases.get_rate(
                    from_code=args.get("from", ""),
                    to_code=args.get("to", ""),
                )
                print(
                    f"Курс {res['from']}→{res['to']}: {res['rate']} "
                    f"(обновлено: {res.get('updated_at')})"
                )

            elif cmd == "update-rates":
                only = args.get("source")  # coingecko / exchangerate-api

                cfg = ParserConfig()
                storage = RatesStorage(
                    rates_path=cfg.rates_path,
                    history_path=cfg.history_path,
                )

                clients = [
                    CoinGeckoClient(
                        cfg.COINGECKO_URL,
                        cfg.CRYPTO_ID_MAP,
                        timeout=cfg.REQUEST_TIMEOUT,
                    ),
                    ExchangeRateApiClient(
                        cfg.EXCHANGERATE_API_URL,
                        cfg.EXCHANGERATE_API_KEY,
                        cfg.BASE_FIAT_CURRENCY,
                        timeout=cfg.REQUEST_TIMEOUT,
                    ),
                ]
                updater = RatesUpdater(clients=clients, storage=storage)
                res = updater.run_update(only_source=only)

                print(
                    "Update successful. Total pairs in cache: "
                    f"{res['total_pairs']}. Updated: {res['updated_pairs']}. "
                    f"Last refresh: {res['last_refresh']}"
                )

            elif cmd == "show-rates":
                cfg = ParserConfig()
                storage = RatesStorage(
                    rates_path=cfg.rates_path,
                    history_path=cfg.history_path,
                )

                snap = storage.load_snapshot()
                pairs = snap.get("pairs", {})
                last_refresh = snap.get("last_refresh")

                if not pairs:
                    print(
                        "Локальный кеш курсов пуст. Выполните 'update-rates', "
                        "чтобы загрузить данные."
                    )
                    continue

                currency = args.get("currency")
                top = args.get("top")

                items = list(pairs.items())

                if currency:
                    cur = currency.strip().upper()
                    items = [
                        (k, v)
                        for k, v in items
                        if k.startswith(cur + "_") or k.endswith("_" + cur)
                    ]
                    if not items:
                        print(f"Курс для '{cur}' не найден в кеше.")
                        continue

                if top:
                    try:
                        n = int(top)
                    except ValueError as err:
                        raise ValueError("--top должен быть числом") from err

                    items.sort(
                        key=lambda kv: float(kv[1].get("rate", 0.0)),
                        reverse=True,
                    )
                    items = items[:n]
                else:
                    items.sort(key=lambda kv: kv[0])

                print(f"Rates from cache (last refresh: {last_refresh}):")

                table = PrettyTable()
                table.field_names = ["PAIR", "RATE", "UPDATED_AT", "SOURCE"]
                for k, v in items:
                    table.add_row(
                        [k, v.get("rate"), v.get("updated_at"), v.get("source")]
                    )
                print(table)

            else:
                print(f"Неизвестная команда: {cmd}")
                _print_help()

        except InsufficientFundsError as e:
            print(e)

        except CurrencyNotFoundError as e:
            print(e)
            print("Подсказка: поддерживаемые коды:", ", ".join(supported_codes()))
            print("Команда: get-rate --from USD --to BTC")

        except ApiRequestError as e:
            print(e)
            print("Повторите позже или выполните 'update-rates' для обновления кеша.")

        except Exception as e:
            print(e)
