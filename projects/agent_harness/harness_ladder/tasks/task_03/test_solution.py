from solution import parse_csv


def test_empty_input():
    assert parse_csv("") == []


def test_header_only():
    assert parse_csv("name,age") == []


def test_basic_rows():
    csv = "name,age,city\nAlice,30,NYC\nBob,25,LA"
    result = parse_csv(csv)
    assert result == [
        {"name": "Alice", "age": "30", "city": "NYC"},
        {"name": "Bob", "age": "25", "city": "LA"},
    ]


def test_quoted_field_with_comma():
    csv = 'name,bio\nAlice,"loves, hiking"'
    result = parse_csv(csv)
    assert result[0]["bio"] == "loves, hiking"


def test_escaped_quote_inside_quoted_field():
    csv = 'name,quote\nBob,"says ""hi"""'
    result = parse_csv(csv)
    assert result[0]["quote"] == 'says "hi"'


def test_whitespace_stripping_unquoted():
    csv = "name , age\n Alice , 30 "
    result = parse_csv(csv)
    assert result[0]["name"] == "Alice"
    assert result[0]["age"] == "30"


def test_empty_field():
    csv = "a,b,c\n1,,3"
    result = parse_csv(csv)
    assert result[0] == {"a": "1", "b": "", "c": "3"}


def test_multiple_rows():
    csv = "x,y\n1,2\n3,4\n5,6"
    result = parse_csv(csv)
    assert len(result) == 3
    assert result[2] == {"x": "5", "y": "6"}
