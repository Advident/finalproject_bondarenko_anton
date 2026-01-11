from __future__ import annotations

from pathlib import Path
from typing import Any


class SettingsLoader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache = {}
            cls._instance._load_defaults()
        return cls._instance

    def _load_defaults(self) -> None:
        # Базовые настройки
        root = Path(__file__).resolve().parents[2]
        self._cache = {
            "DATA_DIR": str(root / "data"),
            "RATES_TTL_SECONDS": 300,  # 5 минут
            "DEFAULT_BASE": "USD",
            "LOG_PATH": str(root / "logs" / "actions.log"),
            "LOG_LEVEL": "INFO",
        }

    def get(self, key: str, default: Any = None) -> Any:
        # Получение значения
        return self._cache.get(key, default)

    def reload(self) -> None:
        # Перезагрузка (пока дефолты)
        self._load_defaults()
