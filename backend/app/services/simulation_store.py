"""Thread-safe bounded simulation session store with LRU and TTL eviction."""

import threading
import time
from collections import OrderedDict
from typing import Any, Dict, Generic, Iterator, List, Optional, Tuple, TypeVar

from app.schemas.health import StoreTelemetry

T = TypeVar("T")


class SimulationSessionStore(Generic[T]):
    """Generic in-memory session store providing LRU capacity bounds and TTL expiration."""

    def __init__(self, max_items: int = 100, ttl_seconds: float = 86400.0) -> None:
        self._max_items = max(1, max_items)
        self._ttl_seconds = max(0.0, ttl_seconds)
        self._store: OrderedDict[str, Tuple[T, float]] = OrderedDict()
        self._key_map: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._total_created = 0
        self._total_evicted = 0
        self._total_expired = 0

    def _norm(self, key: Any) -> str:
        return str(key)

    def set(self, key: Any, value: T, ttl_seconds: Optional[float] = None) -> None:
        """Stores or updates a session item, evicting the oldest LRU item if capacity is reached."""
        norm = self._norm(key)
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl_seconds
        expires_at = time.time() + ttl

        with self._lock:
            if norm in self._store:
                self._store.move_to_end(norm)
                self._store[norm] = (value, expires_at)
                self._key_map[norm] = key
                return

            if len(self._store) >= self._max_items:
                evicted_key, _ = self._store.popitem(last=False)
                self._key_map.pop(evicted_key, None)
                self._total_evicted += 1

            self._store[norm] = (value, expires_at)
            self._key_map[norm] = key
            self._total_created += 1

    def get(self, key: Any, default: Optional[T] = None) -> Optional[T]:
        """Retrieves an item, updating its LRU position, or returns default if missing/expired."""
        norm = self._norm(key)
        with self._lock:
            if norm not in self._store:
                return default

            value, expires_at = self._store[norm]
            if self._ttl_seconds > 0 and time.time() > expires_at:
                del self._store[norm]
                self._key_map.pop(norm, None)
                self._total_expired += 1
                return default

            self._store.move_to_end(norm)
            return value

    def delete(self, key: Any) -> bool:
        """Deletes an item if present. Returns True if removed, False otherwise."""
        norm = self._norm(key)
        with self._lock:
            if norm in self._store:
                del self._store[norm]
                self._key_map.pop(norm, None)
                return True
            return False

    def clear(self) -> None:
        """Clears all stored items."""
        with self._lock:
            self._store.clear()
            self._key_map.clear()

    def prune_expired(self) -> int:
        """Removes all expired items and returns the number pruned."""
        with self._lock:
            if self._ttl_seconds <= 0:
                return 0
            now = time.time()
            expired_keys = [k for k, (_, exp) in self._store.items() if now > exp]
            for k in expired_keys:
                del self._store[k]
                self._key_map.pop(k, None)
                self._total_expired += 1
            return len(expired_keys)

    def get_stats(self) -> StoreTelemetry:
        """Returns observable telemetry counters for this store."""
        with self._lock:
            now = time.time()
            active_count = sum(
                1 for _, exp in self._store.values() if self._ttl_seconds == 0 or now <= exp
            )
            return StoreTelemetry(
                active_sessions=active_count,
                max_capacity=self._max_items,
                total_created=self._total_created,
                total_evicted=self._total_evicted,
                total_expired=self._total_expired,
            )

    def __setitem__(self, key: Any, value: T) -> None:
        self.set(key, value)

    def __getitem__(self, key: Any) -> T:
        val = self.get(key)
        if val is None:
            raise KeyError(key)
        return val

    def __delitem__(self, key: Any) -> None:
        if not self.delete(key):
            raise KeyError(key)

    def __contains__(self, key: Any) -> bool:
        return self.get(key) is not None

    def __len__(self) -> int:
        with self._lock:
            now = time.time()
            return sum(
                1 for _, exp in self._store.values() if self._ttl_seconds == 0 or now <= exp
            )

    def values(self) -> List[T]:
        """Returns a list of all active, unexpired values."""
        with self._lock:
            now = time.time()
            return [
                val for val, exp in self._store.values() if self._ttl_seconds == 0 or now <= exp
            ]

    def keys(self) -> List[Any]:
        """Returns a list of all active, unexpired keys with original key types."""
        with self._lock:
            now = time.time()
            return [
                self._key_map.get(k, k)
                for k, (_, exp) in self._store.items()
                if self._ttl_seconds == 0 or now <= exp
            ]

    def items(self) -> List[Tuple[Any, T]]:
        """Returns key-value pairs of all active, unexpired items."""
        with self._lock:
            now = time.time()
            return [
                (self._key_map.get(k, k), val)
                for k, (val, exp) in self._store.items()
                if self._ttl_seconds == 0 or now <= exp
            ]

    def __iter__(self) -> Iterator[Any]:
        return iter(self.keys())
