from __future__ import annotations

import logging
from datetime import datetime
from functools import wraps
from typing import Any, Callable


def log_action(action: str, verbose: bool = False):
    # Декоратор для доменных операций
    def decorator(func: Callable[..., Any]):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ts = datetime.now().isoformat(timespec="seconds")
            logger = logging.getLogger(__name__)

            username = kwargs.get("username") or kwargs.get("current_username")
            user_id = kwargs.get("user_id") or kwargs.get("current_user_id")
            currency = kwargs.get("currency_code") or kwargs.get("currency")
            amount = kwargs.get("amount")
            base = kwargs.get("base")
            rate = kwargs.get("rate")

            try:
                result = func(*args, **kwargs)

                msg = (
                    f"{ts} {action} user='{username}' user_id={user_id} "
                    f"currency='{currency}' amount={amount} base='{base}' "
                    f"rate={rate} result=OK"
                )
                logger.info(msg)

                if verbose and isinstance(result, dict):
                    extra = result.get("verbose")
                    if extra:
                        logger.info(f"{ts} {action} verbose {extra}")

                return result

            except Exception as e:
                msg = (
                    f"{ts} {action} user='{username}' user_id={user_id} "
                    f"currency='{currency}' amount={amount} base='{base}' "
                    f"rate={rate} result=ERROR "
                    f"error_type={type(e).__name__} error_message={e}"
                )
                logger.info(msg)
                raise

        return wrapper

    return decorator
