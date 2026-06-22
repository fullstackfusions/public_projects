import pytest
from solution import slugify


def test_basic_sentence():
    assert slugify("Hello World") == "hello-world"


def test_lowercase():
    assert slugify("UPPER CASE") == "upper-case"


def test_underscores_to_hyphens():
    assert slugify("hello_world") == "hello-world"


def test_special_chars_removed():
    assert slugify("Hello, World!") == "hello-world"


def test_multiple_spaces_collapse():
    assert slugify("too   many   spaces") == "too-many-spaces"


def test_multiple_hyphens_collapse():
    assert slugify("hello---world") == "hello-world"


def test_leading_trailing_hyphens_stripped():
    assert slugify("--hello world--") == "hello-world"


def test_numbers_preserved():
    assert slugify("Python 3.11 release") == "python-311-release"


def test_mixed_special():
    assert slugify("  The Quick-Brown Fox! ") == "the-quick-brown-fox"


def test_empty_string():
    assert slugify("") == ""


def test_whitespace_only():
    assert slugify("   ") == ""


def test_single_word():
    assert slugify("python") == "python"


def test_already_a_slug():
    assert slugify("already-a-slug") == "already-a-slug"
