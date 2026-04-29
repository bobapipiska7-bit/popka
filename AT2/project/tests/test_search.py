"""Тесты операции search (поиск первого вхождения)."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regex import Regex


def test_simple_search() -> None:
    """Простой поиск."""
    r = Regex("a")
    assert r.search("a") == (0, 1)
    assert r.search("ba") == (1, 2)
    assert r.search("b") is None
    assert r.search("") is None


def test_search_in_middle() -> None:
    """Поиск в середине строки."""
    r = Regex("ab")
    assert r.search("xyzabcde") == (3, 5)
    assert r.search("ab") == (0, 2)
    assert r.search("ba") is None


def test_first_occurrence() -> None:
    """Поиск первого вхождения."""
    r = Regex("a")
    result = r.search("banana")
    assert result == (1, 2)


def test_kleene_star_empty_match() -> None:
    """a* совпадает с пустой строкой на позиции 0."""
    r = Regex("a*")
    result = r.search("bbb")
    assert result == (0, 0)


def test_plus() -> None:
    """Позитивное замыкание."""
    r = Regex("a+")
    assert r.search("baaab") == (1, 4)
    assert r.search("bbb") is None


def test_or() -> None:
    """Или."""
    r = Regex("cat|dog")
    assert r.search("I have a cat") == (9, 12)
    assert r.search("my dog") == (3, 6)
    assert r.search("fish") is None


def test_char_range() -> None:
    """Диапазон символов."""
    r = Regex("[0-9]+")
    assert r.search("abc123def") == (3, 6)
    assert r.search("no digits") is None


def test_repeat() -> None:
    """Повтор."""
    r = Regex("a{3}")
    assert r.search("xaaax") == (1, 4)
    assert r.search("xaax") is None


def test_after_compile() -> None:
    """После compile()."""
    r = Regex("hello").compile()
    assert r.search("say hello world") == (4, 9)


def test_escaping() -> None:
    """Экранирование."""
    r = Regex("a%+b")
    assert r.search("a+b") == (0, 3)
    assert r.search("aab") is None


def test_epsilon_dollar() -> None:
    """Пустая строка $."""
    r = Regex("a$b")
    assert r.search("ab") == (0, 2)
