"""Tests for cache module."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.cache import Cache


class TestCacheBasic:
    """Basic cache functionality tests."""

    def test_set_and_get(self):
        """Test basic set and get."""
        cache = Cache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_nonexistent(self):
        """Test getting non-existent key."""
        cache = Cache()
        assert cache.get("nonexistent") is None

    def test_delete(self):
        """Test deleting a key."""
        cache = Cache()
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_delete_nonexistent(self):
        """Test deleting non-existent key."""
        cache = Cache()
        assert cache.delete("nonexistent") is False

    def test_clear(self):
        """Test clearing cache."""
        cache = Cache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.size() == 0

    def test_size(self):
        """Test cache size."""
        cache = Cache()
        assert cache.size() == 0
        cache.set("key1", "value1")
        assert cache.size() == 1
        cache.set("key2", "value2")
        assert cache.size() == 2


class TestCacheTTL:
    """TTL functionality tests."""

    def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = Cache(default_ttl_seconds=1)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        time.sleep(1.5)
        assert cache.get("key1") is None

    def test_custom_ttl(self):
        """Test custom TTL per entry."""
        cache = Cache(default_ttl_seconds=10)
        cache.set("key1", "value1", ttl_seconds=1)

        time.sleep(1.5)
        assert cache.get("key1") is None


class TestCacheIncrement:
    """Tests for increment operation."""

    def test_increment_existing(self):
        """Test incrementing existing value."""
        cache = Cache()
        cache.set("counter", 5)
        result = cache.increment("counter")
        assert result == 6

    def test_increment_nonexistent(self):
        """Test incrementing non-existent key (should start at 0)."""
        cache = Cache()
        result = cache.increment("counter")
        assert result == 1

    def test_increment_custom_delta(self):
        """Test incrementing with custom delta."""
        cache = Cache()
        cache.set("counter", 10)
        result = cache.increment("counter", delta=5)
        assert result == 15

    def test_increment_race_condition(self):
        """Test that increment has race condition bug.

        This test demonstrates the race condition. Multiple threads
        incrementing the same counter should result in exactly
        num_threads * increments_per_thread, but due to the race
        condition, some increments may be lost.

        This test will FAIL until the race condition is fixed!
        """
        cache = Cache()
        cache.set("counter", 0)

        num_threads = 10
        increments_per_thread = 100

        def increment_many():
            for _ in range(increments_per_thread):
                cache.increment("counter")

        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=increment_many)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        expected = num_threads * increments_per_thread
        actual = cache.get("counter")

        # This should be equal if properly synchronized
        assert actual == expected, (
            f"Race condition detected! Expected {expected}, got {actual}. "
            f"Lost {expected - actual} increments."
        )


class TestCacheGetOrSet:
    """Tests for get_or_set operation."""

    def test_get_or_set_cache_hit(self):
        """Test get_or_set when value exists."""
        cache = Cache()
        cache.set("key1", "existing")

        factory_called = [False]

        def factory():
            factory_called[0] = True
            return "new_value"

        result = cache.get_or_set("key1", factory)
        assert result == "existing"
        assert factory_called[0] is False

    def test_get_or_set_cache_miss(self):
        """Test get_or_set when value doesn't exist."""
        cache = Cache()

        def factory():
            return "computed_value"

        result = cache.get_or_set("key1", factory)
        assert result == "computed_value"
        assert cache.get("key1") == "computed_value"

    def test_get_or_set_race_condition(self):
        """Test that get_or_set has race condition bug.

        Multiple threads calling get_or_set should only call the
        factory once, but due to the race condition, it may be
        called multiple times.

        This test will FAIL until the race condition is fixed!
        """
        cache = Cache()
        factory_calls = [0]
        lock = threading.Lock()

        def expensive_factory():
            with lock:
                factory_calls[0] += 1
            time.sleep(0.1)  # Simulate expensive computation
            return "computed"

        num_threads = 5

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(cache.get_or_set, "key1", expensive_factory)
                for _ in range(num_threads)
            ]
            results = [f.result() for f in futures]

        # All results should be the same
        assert all(r == "computed" for r in results)

        # Factory should only be called once if properly synchronized
        assert factory_calls[0] == 1, (
            f"Race condition detected! Factory called {factory_calls[0]} times "
            f"instead of 1."
        )


class TestCacheThreadSafety:
    """Thread safety tests."""

    def test_concurrent_set_get(self):
        """Test concurrent set and get operations."""
        cache = Cache()
        errors = []

        def writer():
            for i in range(100):
                cache.set(f"key_{threading.current_thread().name}_{i}", i)

        def reader():
            for i in range(100):
                # Just ensure no crashes
                try:
                    cache.get(f"key_Thread-1_{i}")
                except Exception as e:
                    errors.append(e)

        threads = []
        for i in range(5):
            threads.append(threading.Thread(target=writer, name=f"Writer-{i}"))
            threads.append(threading.Thread(target=reader, name=f"Reader-{i}"))

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors during concurrent access: {errors}"
