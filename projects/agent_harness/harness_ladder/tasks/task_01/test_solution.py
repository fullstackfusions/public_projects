import time
import pytest
from solution import fibonacci


def test_base_cases():
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1


def test_sequence():
    expected = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
    for i, val in enumerate(expected):
        assert fibonacci(i) == val, f"fibonacci({i}) should be {val}"


def test_larger_values():
    assert fibonacci(10) == 55
    assert fibonacci(20) == 6765
    assert fibonacci(35) == 9227465


def test_negative_raises():
    with pytest.raises(ValueError):
        fibonacci(-1)


def test_performance():
    start = time.time()
    fibonacci(35)
    elapsed = time.time() - start
    assert elapsed < 1.0, f"fibonacci(35) took {elapsed:.2f}s — missing memoization?"
