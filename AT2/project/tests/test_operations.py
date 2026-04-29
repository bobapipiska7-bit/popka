"""Тесты операций над языками и восстановления РВ."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regex.regex import Regex


def test_complement_basic() -> None:
    """Дополнение — базовый тест."""
    r = Regex("a").compile()
    comp = r.complement()

    assert comp.search("a") is None
    assert comp.search("b") is not None
    assert comp.search("aa") is not None
    assert comp.search("") is not None


def test_complement_double_complement() -> None:
    """Дополнение — двойное дополнение."""
    r = Regex("a+").compile()
    comp = r.complement().compile()
    double_comp = comp.complement().compile()

    assert double_comp._get_compiled().dfa.accepts("a") is True
    assert double_comp._get_compiled().dfa.accepts("aaa") is True

    assert double_comp._get_compiled().dfa.accepts("") is False
    assert double_comp._get_compiled().dfa.accepts("b") is False


def test_difference_basic() -> None:
    """Разность — базовый тест."""
    r1 = Regex("[a-z]+").compile()
    r2 = Regex("hello").compile()
    diff = r1.difference(r2)

    assert diff._get_compiled().dfa.accepts("world") is True
    assert diff._get_compiled().dfa.accepts("hello") is False
    assert diff._get_compiled().dfa.accepts("hell") is True
    assert diff._get_compiled().dfa.accepts("helloo") is True
    assert diff._get_compiled().dfa.accepts("") is False


def test_difference_numbers_except_42() -> None:
    """Разность — числа кроме '42'."""
    r1 = Regex("[0-9]+").compile()
    r2 = Regex("42").compile()
    diff = r1.difference(r2)

    assert diff._get_compiled().dfa.accepts("42") is False
    assert diff._get_compiled().dfa.accepts("43") is True
    assert diff._get_compiled().dfa.accepts("123") is True
    assert diff._get_compiled().dfa.accepts("4") is True


def test_difference_with_self_empty_language() -> None:
    """Разность с самим собой: L \\ L = ∅."""
    r = Regex("a+").compile()
    diff = r.difference(r)

    assert diff._get_compiled().dfa.accepts("a") is False
    assert diff._get_compiled().dfa.accepts("aaa") is False


def check_restore(pattern: str, test_strings: list[tuple[str, bool]]) -> None:
    """
    Компилируем оригинал, восстанавливаем РВ,
    компилируем восстановленное, сравниваем поведение.
    """
    original = Regex(pattern).compile()
    restored_pattern = original.restore()
    restored = Regex(restored_pattern).compile()

    for string, expected in test_strings:
        result = restored._get_compiled().dfa.accepts(string)
        assert result == expected, (
            f"pattern='{pattern}', "
            f"restored='{restored_pattern}', "
            f"string='{string}': "
            f"ожидали {expected}, получили {result}"
        )


def test_restore_simple_cases() -> None:
    """Восстановление РВ — простые случаи."""
    check_restore("a", [
        ("a", True),
        ("b", False),
        ("", False),
    ])

    check_restore("a|b", [
        ("a", True),
        ("b", True),
        ("c", False),
    ])

    check_restore("a*", [
        ("", True),
        ("a", True),
        ("aaa", True),
        ("b", False),
    ])

    check_restore("ab", [
        ("ab", True),
        ("a", False),
        ("b", False),
    ])

    check_restore("(a|b)*c", [
        ("c", True),
        ("ac", True),
        ("bc", True),
        ("abc", True),
        ("ab", False),
        ("", False),
    ])


def test_restore_returns_string() -> None:
    """Восстановление возвращает строку."""
    r = Regex("a+").compile()
    restored = r.restore()
    assert isinstance(restored, str)
    assert len(restored) > 0


def test_operations_auto_compile() -> None:
    """Операции без compile() вызывают compile() автоматически."""
    r1 = Regex("a+")
    r2 = Regex("aaa")
    diff = r1.difference(r2)
    assert diff._get_compiled().dfa.accepts("a") is True
    assert diff._get_compiled().dfa.accepts("aaa") is False


def test_search_on_operations_result() -> None:
    """search на результате операций."""
    r1 = Regex("[a-z]+").compile()
    r2 = Regex("hello").compile()
    diff = r1.difference(r2)
    result = diff.search("say hello world")
    assert result is not None


def test_restore_after_operations() -> None:
    """restore после операций."""
    r1 = Regex("a|b").compile()
    r2 = Regex("b").compile()
    diff = r1.difference(r2)

    restored = diff.restore()
    assert isinstance(restored, str)

    restored_regex = Regex(restored).compile()
    assert restored_regex._get_compiled().dfa.accepts("a") is True
    assert restored_regex._get_compiled().dfa.accepts("b") is False
