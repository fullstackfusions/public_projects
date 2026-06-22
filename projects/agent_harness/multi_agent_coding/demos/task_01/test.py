# Pytest is run with cwd=workspace, so `from solution import ...` finds solution.py there.
import pytest
from solution import validate_email


def test_valid_simple():
    assert validate_email("user@example.com") is True


def test_valid_subdomains():
    assert validate_email("user@mail.example.co.uk") is True


def test_valid_plus_sign():
    assert validate_email("user+tag@example.org") is True


def test_valid_dots_in_local():
    assert validate_email("first.last@example.com") is True


def test_empty_string():
    assert validate_email("") is False


def test_no_at_symbol():
    assert validate_email("userexample.com") is False


def test_multiple_at_symbols():
    assert validate_email("user@@example.com") is False


def test_leading_whitespace():
    assert validate_email(" user@example.com") is False


def test_trailing_whitespace():
    assert validate_email("user@example.com ") is False


def test_missing_tld():
    assert validate_email("user@example") is False


def test_short_tld_one_char():
    assert validate_email("user@example.c") is False


def test_at_start():
    assert validate_email("@example.com") is False


def test_at_end():
    assert validate_email("user@") is False
