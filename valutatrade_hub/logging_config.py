from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_path: str, level: str = "INFO") -> None:
    # Единая настройка логов
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    fmt = logging.Formatter("%(levelname)s %(asctime)s %(message)s")

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=512_000,  # ~0.5MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)

    # Чтобы не дублировать хендлеры при повторных импортах
    logger.handlers = []
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
