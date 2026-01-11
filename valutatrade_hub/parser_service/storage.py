from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    # ISO-UTC с Z
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def atomic_write_json(path: Path, data: Any) -> None:
    # Атомарная запись (tmp -> rename)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def read_json_safe(path: Path, default: Any) -> Any:
    # Чтение JSON с дефолтом
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except ValueError:
        return default


class RatesStorage:
    # Хранилище rates.json и history exchange_rates.json
    def __init__(self, rates_path: Path, history_path: Path) -> None:
        self._rates_path = rates_path
        self._history_path = history_path

    def load_snapshot(self) -> dict:
        # {"pairs": {...}, "last_refresh": ...}
        return read_json_safe(self._rates_path, {"pairs": {}, "last_refresh": None})

    def save_snapshot(self, snapshot: dict) -> None:
        atomic_write_json(self._rates_path, snapshot)

    def load_history(self) -> list[dict]:
        # Список записей
        return read_json_safe(self._history_path, [])

    def append_history(self, entries: list[dict]) -> int:
        # Добавляем новые записи без дублей по id
        history = self.load_history()
        existed = {x.get("id") for x in history if isinstance(x, dict)}

        added = 0
        for e in entries:
            if e.get("id") in existed:
                continue
            history.append(e)
            existed.add(e.get("id"))
            added += 1

        atomic_write_json(self._history_path, history)
        return added
