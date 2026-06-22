import pytest
from solution import encode, decode


def test_encode_repeated():
    assert encode("aaabbc") == "3a2bc"


def test_encode_no_repeat():
    assert encode("abc") == "abc"


def test_encode_single_char():
    assert encode("a") == "a"


def test_encode_all_same():
    assert encode("aaaaa") == "5a"


def test_encode_empty():
    assert encode("") == ""


def test_encode_single_run_no_prefix():
    assert encode("aabba") == "2a2ba"


def test_decode_basic():
    assert decode("3a2bc") == "aaabbc"


def test_decode_no_numbers():
    assert decode("abc") == "abc"


def test_decode_all_same():
    assert decode("5a") == "aaaaa"


def test_decode_empty():
    assert decode("") == ""


def test_decode_mixed():
    assert decode("2a2b") == "aabb"


def test_roundtrip_basic():
    s = "aaabbc"
    assert decode(encode(s)) == s


def test_roundtrip_no_repeat():
    s = "abcdef"
    assert decode(encode(s)) == s


def test_roundtrip_long():
    s = "aaaaabbbbcccccdeeeeeeee"
    assert decode(encode(s)) == s


def test_roundtrip_mixed():
    s = "Hello World"
    assert decode(encode(s)) == s
