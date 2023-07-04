from vocexcel.utils import split_and_tidy


def test_default_action():
    assert split_and_tidy(None) == []
    assert split_and_tidy("") == []
    assert split_and_tidy("a,b") == ["a", "b"]
    assert split_and_tidy(" a , b ") == ["a", "b"]


def test_trailing_comma():
    assert split_and_tidy("a,") == ["a"]
    assert split_and_tidy("a,b,") == ["a", "b"]
