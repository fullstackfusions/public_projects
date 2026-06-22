import pytest
from solution import LRUCache


def test_basic_get_put():
    cache = LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    assert cache.get(1) == 1


def test_miss_returns_negative_one():
    cache = LRUCache(3)
    assert cache.get(99) == -1


def test_eviction_evicts_lru():
    cache = LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    cache.get(1)       # 1 is now MRU; 2 is LRU
    cache.put(3, 3)    # evicts 2
    assert cache.get(2) == -1
    assert cache.get(1) == 1
    assert cache.get(3) == 3


def test_update_existing_key():
    cache = LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    cache.put(1, 10)   # update, not a new key
    assert cache.get(1) == 10
    assert cache.get(2) == 2


def test_capacity_one():
    cache = LRUCache(1)
    cache.put(1, 1)
    cache.put(2, 2)    # evicts 1
    assert cache.get(1) == -1
    assert cache.get(2) == 2


def test_lru_ordering():
    cache = LRUCache(3)
    cache.put(1, 1)
    cache.put(2, 2)
    cache.put(3, 3)
    cache.get(1)       # order: 2, 3, 1
    cache.get(2)       # order: 3, 1, 2
    cache.put(4, 4)    # evicts 3
    assert cache.get(3) == -1
    assert cache.get(1) == 1
    assert cache.get(2) == 2
    assert cache.get(4) == 4
