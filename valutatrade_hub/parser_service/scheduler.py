from __future__ import annotations

import logging
import time

from .updater import RatesUpdater


class SimpleScheduler:
    # Простой цикл обновления
    def __init__(self, updater: RatesUpdater, interval_seconds: int = 300) -> None:
        self._updater = updater
        self._interval = int(interval_seconds)
        self._log = logging.getLogger(__name__)

    def run_forever(self) -> None:
        self._log.info(f"Scheduler started. Interval={self._interval}s")
        while True:
            try:
                self._updater.run_update()
            except Exception as e:
                self._log.error(f"Scheduler update failed: {e}")
            time.sleep(self._interval)
