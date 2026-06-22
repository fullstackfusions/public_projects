import time
import pytest
from solution import TokenBucket


def test_starts_full():
    bucket = TokenBucket(rate=10.0, capacity=10.0)
    assert bucket.acquire(10.0) is True


def test_acquire_within_capacity():
    bucket = TokenBucket(rate=10.0, capacity=10.0)
    assert bucket.acquire(5.0) is True
    assert bucket.acquire(5.0) is True


def test_reject_when_empty():
    bucket = TokenBucket(rate=1.0, capacity=5.0)
    assert bucket.acquire(5.0) is True
    assert bucket.acquire(1.0) is False


def test_no_partial_consumption():
    bucket = TokenBucket(rate=1.0, capacity=5.0)
    assert bucket.acquire(5.0) is True
    # bucket is now empty; a failed acquire must not partially consume
    bucket.acquire(3.0)        # fails
    assert bucket.acquire(1.0) is False   # still empty


def test_refill_over_time():
    bucket = TokenBucket(rate=100.0, capacity=10.0)
    assert bucket.acquire(10.0) is True   # drain
    time.sleep(0.15)                       # refill ~15 tokens, capped at 10
    assert bucket.acquire(10.0) is True   # should be full again


def test_capacity_cap():
    bucket = TokenBucket(rate=100.0, capacity=5.0)
    time.sleep(0.1)            # would add 10 tokens, capped at 5
    assert bucket.acquire(5.0) is True
    assert bucket.acquire(1.0) is False   # no tokens left


def test_exceed_capacity_always_rejected():
    bucket = TokenBucket(rate=1.0, capacity=5.0)
    assert bucket.acquire(6.0) is False   # more than capacity
