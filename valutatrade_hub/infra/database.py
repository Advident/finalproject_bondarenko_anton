from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..infra.settings import SettingsLoader


class DatabaseManager:
    # Singleton для работы с JSON
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = SettingsLoader()
            cls._instance._init_paths()
        return cls._instance

    def _init_paths(self) -> None:
        # Пути к JSON
        data_dir = Path(self._settings.get("DATA_DIR"))
        data_dir.mkdir(parents=True, exist_ok=True)

        self.users_path = data_dir / "users.json"
        self.portfolios_path = data_dir / "portfolios.json"
        self.rates_path = data_dir / "rates.json"

        self._ensure_file(self.users_path, "[]")
        self._ensure_file(self.portfolios_path, "[]")
        self._ensure_file(self.rates_path, "{}")

    def _ensure_file(self, path: Path, default_text: str) -> None:
        # Создаём файл или лечим пустой
        if not path.exists():
            path.write_text(default_text, encoding="utf-8")
            return
        if path.read_text(encoding="utf-8").strip() == "":
            path.write_text(default_text, encoding="utf-8")

    def read(self, path: Path) -> Any:
        # Безопасное чтение JSON
        text = path.read_text(encoding="utf-8").strip()
        return json.loads(text)

    def write(self, path: Path, data: Any) -> None:
        # Запись JSON
        text = json.dumps(data, ensure_ascii=False, indent=2)
        path.write_text(text, encoding="utf-8")
