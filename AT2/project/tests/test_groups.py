"""Тесты групп захвата для search(groups=True)."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regex import Regex


def test_simple_group() -> None:
    """Простая группа."""
    r = Regex("(a)")
    match = r.search("a", groups=True)
    assert match is not None
    assert match[0] == "a"
    assert match[1] == "a"


def test_group_in_context() -> None:
    """Группа в контексте."""
    r = Regex("(a+)b")
    match = r.search("aaab", groups=True)
    assert match is not None
    assert match[0] == "aaab"
    assert match[1] == "aaa"


def test_multiple_groups() -> None:
    """Несколько групп."""
    r = Regex("(a+)(b+)")
    match = r.search("aaabb", groups=True)
    assert match is not None
    assert match[0] == "aaabb"
    assert match[1] == "aaa"
    assert match[2] == "bb"


def test_iter_groups() -> None:
    """Итерация по группам."""
    r = Regex("(a)(b)(c)")
    match = r.search("abc", groups=True)
    assert match is not None
    groups = list(match)
    assert groups[0] == "abc"
    assert groups[1] == "a"
    assert groups[2] == "b"
    assert groups[3] == "c"


def test_search_without_groups_default() -> None:
    """Поиск без групп (groups=False по умолчанию)."""
    r = Regex("(a+)b")
    result = r.search("aaab")
    assert result == (0, 4)
    assert not isinstance(result, object.__class__)


def test_match_start_end() -> None:
    """match.start и match.end."""
    r = Regex("(hello)")
    match = r.search("say hello", groups=True)
    assert match.start == 4
    assert match.end == 9
    assert match.string == "hello"


def test_match_source() -> None:
    """match.source."""
    r = Regex("(a+)")
    match = r.search("baaab", groups=True)
    assert match.source == "baaab"
    assert match.string == "aaa"


def test_nested_groups() -> None:
    """Вложенные группы."""
    r = Regex("((a+)b)")
    match = r.search("aaab", groups=True)
    assert match is not None
    assert match[0] == "aaab"
    assert match[1] == "aaab"
    assert match[2] == "aaa"


def test_not_found() -> None:
    """Если не найдено."""
    r = Regex("(xyz)")
    match = r.search("hello", groups=True)
    assert match is None
    assert not match


def test_bool_match() -> None:
    """bool(match)."""
    r = Regex("(a)")
    match = r.search("a", groups=True)
    assert bool(match) is True

    no_match = r.search("b", groups=True)
    assert no_match is None
