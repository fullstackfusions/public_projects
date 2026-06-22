import time
import pytest
from solution import retry


def test_success_on_first_try():
    @retry()
    def always_works():
        return 42

    assert always_works() == 42


def test_retries_then_succeeds():
    calls = []

    @retry(max_attempts=3)
    def fails_twice():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("not yet")
        return "ok"

    assert fails_twice() == "ok"
    assert len(calls) == 3


def test_raises_after_max_attempts():
    @retry(max_attempts=3)
    def always_fails():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        always_fails()


def test_only_catches_specified_exceptions():
    @retry(max_attempts=3, exceptions=(ValueError,))
    def raises_type_error():
        raise TypeError("wrong type")

    with pytest.raises(TypeError):
        raises_type_error()


def test_returns_value():
    @retry(max_attempts=2)
    def returns_list():
        return [1, 2, 3]

    assert returns_list() == [1, 2, 3]


def test_no_delay_on_success():
    @retry(max_attempts=3, delay=10.0)
    def instant():
        return True

    start = time.time()
    instant()
    assert time.time() - start < 1.0, "Should not sleep after a successful call"


def test_max_attempts_one():
    @retry(max_attempts=1)
    def always_fails():
        raise ValueError("x")

    with pytest.raises(ValueError):
        always_fails()
