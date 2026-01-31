"""Cache module with intentional race condition bug."""

from datetime import datetime, timedelta
from collections.abc import Callable
from typing import Any


class Cache:
    """Simple in-memory cache with TTL support.

    BUG: This cache has a race condition! When multiple threads
    try to update the same key simultaneously, the read-modify-write
    operation is not atomic, leading to lost updates.
    """

    def __init__(self, default_ttl_seconds: int = 300):
        """Initialize cache.

        Args:
            default_ttl_seconds: Default time-to-live for cache entries
        """
        self._store: dict[str, tuple[Any, datetime]] = {}
        self._default_ttl = timedelta(seconds=default_ttl_seconds)

    def get(self, key: str) -> Any | None:
        """Get a value from cache.

        Args:
            key: The cache key

        Returns:
            The cached value, or None if not found or expired
        """
        if key not in self._store:
            return None

        value, expires_at = self._store[key]

        if datetime.now() > expires_at:
            del self._store[key]
            return None

        return value

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Set a value in cache.

        Args:
            key: The cache key
            value: The value to cache
            ttl_seconds: Optional TTL override
        """
        ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else self._default_ttl
        expires_at = datetime.now() + ttl
        self._store[key] = (value, expires_at)

    def delete(self, key: str) -> bool:
        """Delete a key from cache.

        Args:
            key: The cache key to delete

        Returns:
            True if key was found and deleted, False otherwise
        """
        if key in self._store:
            del self._store[key]
            return True
        return False

    def increment(self, key: str, delta: int = 1) -> int:
        """Increment a numeric value in cache.

        BUG: This operation is NOT atomic! Race condition here.

        Args:
            key: The cache key
            delta: Amount to increment by

        Returns:
            The new value after incrementing
        """
        # BUG: Read-modify-write without synchronization
        current = self.get(key)
        if current is None:
            current = 0

        new_value = current + delta

        # Another thread could have modified the value between read and write
        self.set(key, new_value)

        return new_value

    def get_or_set(self, key: str, factory: Callable[[], Any], ttl_seconds: int | None = None) -> Any:
        """Get a value from cache, or set it using the factory function.

        BUG: This operation is NOT atomic! Race condition here.

        Args:
            key: The cache key
            factory: Function to generate value if not cached
            ttl_seconds: Optional TTL override

        Returns:
            The cached or newly generated value
        """
        # BUG: Check-then-set without synchronization
        value = self.get(key)
        if value is not None:
            return value

        # Multiple threads could execute factory and overwrite each other
        new_value = factory()
        self.set(key, new_value, ttl_seconds)
        return new_value

    def clear(self) -> None:
        """Clear all cache entries."""
        self._store.clear()

    def size(self) -> int:
        """Get the number of entries in cache.

        Returns:
            Number of cached entries
        """
        return len(self._store)


# Global cache instance
cache = Cache()
