from calc import divide, parse_int, clamp


def test_divide():
    assert divide(6, 3) == 2


def test_parse_int():
    assert parse_int("42") == 42


def test_clamp_inside():
    assert clamp(5, 0, 10) == 5
