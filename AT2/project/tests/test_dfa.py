"""Тесты построения и минимизации ДКА."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regex.compiled import compile_regex


def test_literal() -> None:
    """Простой литерал."""
    compiled = compile_regex("a")
    assert compiled.accepts("a") is True
    assert compiled.accepts("b") is False
    assert compiled.accepts("") is False
    assert compiled.accepts("aa") is False


def test_or() -> None:
    """Или."""
    compiled = compile_regex("a|b")
    assert compiled.accepts("a") is True
    assert compiled.accepts("b") is True
    assert compiled.accepts("c") is False
    assert compiled.accepts("ab") is False


def test_concat() -> None:
    """Конкатенация."""
    compiled = compile_regex("ab")
    assert compiled.accepts("ab") is True
    assert compiled.accepts("a") is False
    assert compiled.accepts("b") is False
    assert compiled.accepts("ba") is False


def test_star() -> None:
    """Замыкание Клини."""
    compiled = compile_regex("a*")
    assert compiled.accepts("") is True
    assert compiled.accepts("a") is True
    assert compiled.accepts("aaa") is True
    assert compiled.accepts("b") is False


def test_plus() -> None:
    """Позитивное замыкание."""
    compiled = compile_regex("a+")
    assert compiled.accepts("") is False
    assert compiled.accepts("a") is True
    assert compiled.accepts("aaa") is True


def test_char_range() -> None:
    """Диапазон символов."""
    compiled = compile_regex("[a-c]")
    assert compiled.accepts("a") is True
    assert compiled.accepts("b") is True
    assert compiled.accepts("c") is True
    assert compiled.accepts("d") is False


def test_repeat_fixed() -> None:
    """Повтор фиксированный."""
    compiled = compile_regex("a{3}")
    assert compiled.accepts("aaa") is True
    assert compiled.accepts("aa") is False
    assert compiled.accepts("aaaa") is False


def test_repeat_range() -> None:
    """Повтор диапазон."""
    compiled = compile_regex("a{2,4}")
    assert compiled.accepts("a") is False
    assert compiled.accepts("aa") is True
    assert compiled.accepts("aaa") is True
    assert compiled.accepts("aaaa") is True
    assert compiled.accepts("aaaaa") is False


def test_repeat_open() -> None:
    """Повтор открытый."""
    compiled = compile_regex("a{2,}")
    assert compiled.accepts("a") is False
    assert compiled.accepts("aa") is True
    assert compiled.accepts("aaaaaaa") is True


def test_group() -> None:
    """Группа захвата."""
    compiled = compile_regex("(ab)")
    assert compiled.accepts("ab") is True
    assert compiled.accepts("a") is False


def test_complex_expression() -> None:
    """Сложное выражение."""
    compiled = compile_regex("(a|b)*c")
    assert compiled.accepts("c") is True
    assert compiled.accepts("ac") is True
    assert compiled.accepts("bc") is True
    assert compiled.accepts("abc") is True
    assert compiled.accepts("ababc") is True
    assert compiled.accepts("ab") is False
    assert compiled.accepts("") is False


def test_escaping() -> None:
    """Экранирование."""
    compiled = compile_regex("a%|b")
    assert compiled.accepts("a|b") is True
    assert compiled.accepts("a") is False
    assert compiled.accepts("b") is False


def test_epsilon_symbol() -> None:
    """Пустая строка."""
    compiled = compile_regex("a$b")
    assert compiled.accepts("ab") is True
    assert compiled.accepts("a") is False


def test_alpha_range_plus() -> None:
    """Диапазон [a-zA-Z]."""
    compiled = compile_regex("[a-zA-Z]+")
    assert compiled.accepts("hello") is True
    assert compiled.accepts("Hello") is True
    assert compiled.accepts("hello123") is False
    assert compiled.accepts("") is False


def test_minimization_state_count() -> None:
    """Минимизация — проверка количества состояний."""
    dfa1 = compile_regex("a")
    dfa2 = compile_regex("a|a")
    assert len(dfa1.dfa.states) == len(dfa2.dfa.states)


def test_minimized_dfa_works() -> None:
    """Проверка что минимизированный ДКА работает."""
    compiled = compile_regex("[0-9]+")
    assert compiled.accepts("0") is True
    assert compiled.accepts("123") is True
    assert compiled.accepts("abc") is False
    assert compiled.accepts("") is False
