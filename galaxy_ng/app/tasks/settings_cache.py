"""
Tasks related to the settings cache management.
"""
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from django.conf import settings
from redis import ConnectionError, Redis

from galaxy_ng.app.models.config import Setting
from django.db.utils import OperationalError

logger = logging.getLogger(__name__)
_conn = None
CACHE_KEY = "GALAXY_SETTINGS_DATA"


def get_redis_connection():
    global _conn
    redis_host = settings.get("REDIS_HOST")
    redis_url = settings.get("REDIS_URL")
    if _conn is None:
        if redis_url is not None:
            _conn = Redis.from_url(redis_url, decode_responses=True)
        elif redis_host is not None:
            _conn = Redis(
                host=redis_host,
                port=settings.get("REDIS_PORT") or 6379,
                db=settings.get("REDIS_DB", 0),
                password=settings.get("REDIS_PASSWORD"),
                ssl=settings.get("REDIS_SSL", False),
                ssl_ca_certs=settings.get("REDIS_SSL_CA_CERTS"),
                decode_responses=True,
            )
        else:
            logger.warning(
                "REDIS connection undefined, not caching dynamic settings"
            )
    return _conn


conn: Optional[Redis] = get_redis_connection()


def connection_error_wrapper(
    func: Optional[Callable] = None, default: Callable = lambda: 0
) -> Callable:
    """A decorator that enables sync functions which use Redis to swallow connection errors."""

    def dispatch(func, *args, **kwargs):
        """Handle connection errors, specific to the sync context, raised by the Redis client."""
        if conn is None:  # No redis connection defined
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
def acquire_lock(lock_name: str, lock_timeout: int = 20):
    """Acquire a lock using Redis connection"""
    LOCK_KEY = f"GALAXY_SETTINGS_LOCK_{lock_name}"
    if conn is None:
        return "no-lock"  # no Redis connection, assume lock is acquired

    token = str(uuid4())
    lock = conn.set(LOCK_KEY, token, nx=True, ex=lock_timeout)
    return token if lock else False


@connection_error_wrapper
def release_lock(lock_name: str, token: str):
    """Release a lock using Redis connection"""
    LOCK_KEY = f"GALAXY_SETTINGS_LOCK_{lock_name}"
    if conn is None:
        return
    lock = conn.get(LOCK_KEY)
    if lock == token:
        conn.delete(LOCK_KEY)


@connection_error_wrapper
def update_setting_cache(data: Dict[str, Any]) -> int:
    """Takes a python dictionary and write to Redis
    as a hashmap using Redis connection"""
    if conn is None:
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
        return {}

    return conn.hgetall(CACHE_KEY)


def get_settings_from_db():
    """Returns the data in the Setting table."""
    try:
        data = Setting.as_dict()
        return data
    except OperationalError as exc:
        logger.error("Could not read settings from database: %s", str(exc))
        return {}
