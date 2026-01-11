# ValutaTrade Hub

ValutaTrade Hub — консольное приложение (CLI) для регистрации пользователей, управления виртуальным валютным портфелем и получения актуальных курсов валют. Проект разделён на Core Service (бизнес-логика) и Parser Service (обновление курсов из внешних API).

## Возможности
- регистрация и вход пользователей (`register`, `login`)
- просмотр портфеля и общей стоимости (`show-portfolio`)
- покупка и продажа валют (`buy`, `sell`)
- получение курса валют (`get-rate`)
- обновление и просмотр кеша курсов (`update-rates`, `show-rates`)

## Структура

## Структура проекта

```text
finalproject_<фамилия>_<группа>/
├── data/
│   ├── users.json           # пользователи
│   ├── portfolios.json      # портфели и кошельки
│   ├── rates.json           # актуальный кеш курсов
│   └── exchange_rates.json  # история курсов (Parser Service)
│
├── valutatrade_hub/
│   ├── core/                # модели, бизнес-логика, валюты
│   │   ├── models.py
│   │   ├── usecases.py
│   │   ├── currencies.py
│   │   └── exceptions.py
│   │
│   ├── infra/               # настройки и JSON-хранилище
│   │   ├── settings.py
│   │   └── database.py
│   │
│   ├── parser_service/      # клиенты API и обновление курсов
│   │   ├── api_clients.py
│   │   ├── config.py
│   │   ├── updater.py
│   │   └── storage.py
│   │
│   ├── cli/                 # CLI-интерфейс
│   │   └── interface.py
│   │
│   ├── decorators.py        # декораторы (логирование)
│   └── logging_config.py    # настройка логов
│
├── main.py                  # точка входа
├── pyproject.toml
├── Makefile
├── README.md
└── .gitignore
```

## Установка и запуск

- poetry install
- poetry run project

## Основные команды CLI

- register --username alice --password 1234
- login --username alice --password 1234
- show-portfolio --base USD
- buy --currency BTC --amount 0.05
- sell --currency BTC --amount 0.01
- get-rate --from BTC --to USD

## Кеш курсов, Parser Service и служебные команды

Актуальные курсы хранятся в `data/rates.json`. Если курс старше TTL (`RATES_TTL_SECONDS` в `infra/settings.py`), Core Service сообщает об устаревших данных и предлагает обновить кеш.

**Parser Service** использует внешние источники курсов:
- CoinGecko — криптовалюты
- ExchangeRate-API — фиатные валюты

Ключ для ExchangeRate-API задаётся через переменную окружения:

export EXCHANGERATE_API_KEY="ВАШ_КЛЮЧ"

**Команды Parser Service:**
- update-rates
- show-rates --currency BTC
- show-rates --top 3

**Проверка и сборка проекта:**
- poetry run ruff check .
- poetry build

**Выход из CLI:**
- exit