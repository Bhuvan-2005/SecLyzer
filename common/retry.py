"""
Retry decorator with exponential backoff for SecLyzer
Provides resilient database and network operations
"""

import functools
import time
from typing import Callable, Tuple, Type

from common.logger import get_logger

logger = get_logger(__name__)


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorator for retrying functions with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each attempt
        exceptions: Tuple of exceptions to catch and retry

    Example:
        @retry_with_backoff(max_attempts=3, initial_delay=0.5)
        def write_to_db(data):
            db.write(data)
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts",
                            function=func.__name__,
                            attempts=max_attempts,
                            error=str(e),
                        )
                        raise

                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt}/{max_attempts}), retrying in {delay}s",
                        function=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay=delay,
                        error=str(e),
                    )

                    time.sleep(delay)
                    delay *= backoff_factor

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator
