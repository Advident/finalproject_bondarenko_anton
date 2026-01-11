from __future__ import annotations

import logging
from typing import Any

from .storage import RatesStorage, utc_now_iso


class RatesUpdater:
    # Точка входа обновления
    def __init__(self, clients: list, storage: RatesStorage) -> None:
        self._clients = clients
        self._storage = storage
        self._log = logging.getLogger(__name__)

    def run_update(self, only_source: str | None = None) -> dict[str, Any]:
        """
        Обновляет:
        - rates.json (snapshot)
        - exchange_rates.json (history)
        """
        self._log.info("Starting rates update...")

        snapshot = self._storage.load_snapshot()
        pairs = snapshot.get("pairs", {})
        if not isinstance(pairs, dict):
            pairs = {}

        history_entries: list[dict] = []
        total_updated = 0
        ts = utc_now_iso()

        for client in self._clients:
            try:
                rates, meta = client.fetch_rates()

                source = str(meta.get("source", "Unknown")).lower()
                if only_source and source != only_source.lower():
                    continue

                self._log.info(
                    "Fetching from %s... OK (%s rates)",
                    meta.get("source"),
                    len(rates),
                )

                # Обновляем snapshot по правилу "свежее побеждает"
                for pair, rate in rates.items():
                    pair = str(pair).upper()
                    entry = pairs.get(pair)

                    new_entry = {
                        "rate": float(rate),
                        "updated_at": ts,
                        "source": meta.get("source"),
                    }

                    if not isinstance(entry, dict) or entry.get("updated_at") is None:
                        pairs[pair] = new_entry
                        total_updated += 1
                    else:
                        # ISO-строки сопоставимы при одном формате UTC-Z
                        if str(entry.get("updated_at")) < ts:
                            pairs[pair] = new_entry
                            total_updated += 1

                    from_cur, to_cur = pair.split("_", 1)
                    hist_id = f"{pair}_{ts}"
                    history_entries.append(
                        {
                            "id": hist_id,
                            "from_currency": from_cur,
                            "to_currency": to_cur,
                            "rate": float(rate),
                            "timestamp": ts,
                            "source": meta.get("source"),
                            "meta": {
                                "request_ms": meta.get("request_ms"),
                                "status_code": meta.get("status_code"),
                                "etag": meta.get("etag"),
                                "raw": meta.get("raw"),
                            },
                        }
                    )

            except Exception as e:
                self._log.error(f"Failed to fetch: {e}")

        snapshot["pairs"] = pairs
        snapshot["last_refresh"] = utc_now_iso()

        self._log.info("Writing %s pairs to rates.json...", len(pairs))
        self._storage.save_snapshot(snapshot)

        added = self._storage.append_history(history_entries)
        self._log.info("History appended: %s new records", added)

        if total_updated == 0:
            self._log.info("Update completed with errors or no changes.")
        else:
            self._log.info("Update successful.")

        return {
            "total_pairs": len(pairs),
            "updated_pairs": total_updated,
            "last_refresh": snapshot["last_refresh"],
            "history_added": added,
        }
