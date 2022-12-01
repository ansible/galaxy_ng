"""
Tasks related to the settings cache management.
"""
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional

from django.conf import settings
from redis import ConnectionError, Redis

_conn = None


def get_redis_connection():
    global _conn
    if _conn is None:
        if redis_url := settings.get("REDIS_URL"):
            _conn = Redis.from_url(redis_url, decode_responses=True)
        else:
            _conn = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                ssl=settings.REDIS_SSL,
                ssl_ca_certs=settings.REDIS_SSL_CA_CERTS,
                decode_responses=True,
            )
    return _conn


conn: Optional[Redis] = get_redis_connection()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
CACHE_KEY = "GALAXY_SETTINGS"


def connection_error_wrapper(
    func: Optional[Callable] = None, default: Callable = lambda: 0
) -> Callable:
    """A decorator that enables sync functions which use Redis to swallow connection errors."""

    def dispatch(func, *args, **kwargs):
        """Handle connection errors, specific to the sync context, raised by the Redis client."""
        if conn is None:
            logger.debug(f"{func.__name__} skipped, no Redis connection available")
            return default()
        try:
            return func(*args, **kwargs)
        except (ConnectionError, TypeError) as e:
            # TypeError is raised when an invalid port number for the Redis connection is configured
            logging.error(f"Redis connection error: {e}")
            return default()

    if func:

        @wraps(func)
        def simple_wrapper(*args, **kwargs):
            """This is for decorator used without parenthesis"""
            return dispatch(func, *args, **kwargs)

        return simple_wrapper

    def wrapper(func):
        """This is for decorator used with parenthesis"""

        @wraps(func)
        def wrapped(*args, **kwargs):
            return dispatch(func, *args, **kwargs)

        return wrapped

    return wrapper


@connection_error_wrapper
def update_setting_cache(data: Dict[str, Any]) -> int:
    """Takes a python dictionary and write to Redis
    as a hashmap using Redis connection"""
    if conn is None:
        logger.debug("Settings cache update skipped, no Redis connection available")
        return 0

    conn.delete(CACHE_KEY)
    updated = 0
    if data:
        updated = conn.hset(CACHE_KEY, mapping=data)
        conn.expire(CACHE_KEY, settings.get("GALAXY_SETTINGS_EXPIRE", 60 * 60 * 24))
    return updated


@connection_error_wrapper(default=dict)
def get_settings_from_cache() -> Dict[str, Any]:
    """Reads settings from Redis cache and returns a python dictionary"""
    if conn is None:
        logger.debug("Settings cache read skipped, no Redis connection available")
        return {}

    return conn.hgetall(CACHE_KEY)
