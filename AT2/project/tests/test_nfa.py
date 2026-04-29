"""Тесты построения НКА по алгоритму Томпсона."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regex.ast_nodes import CharRange, Concat, Epsilon, Group, Literal, Or, Plus, Repeat, Star
from regex.nfa import EPSILON, NFABuilder, NFAState, epsilon_closure, get_alphabet, move
from regex.parser import Parser


def simulate_nfa(nfa, string: str) -> bool:
    """Симулирует НКА на строке и возвращает факт принятия."""
    current = epsilon_closure({nfa.start})
    for char in string:
        current = epsilon_closure(move(current, char))
    return any(state.is_final for state in current)


class TestNFA(unittest.TestCase):
    """Проверяет построение НКА для всех узлов AST."""

    def setUp(self) -> None:
        """Создает новый построитель перед каждым тестом."""
        self.builder = NFABuilder()

    def test_literal(self) -> None:
        """Literal: принимается только один нужный символ."""
        nfa = self.builder.build(Literal("a"))
        self.assertTrue(simulate_nfa(nfa, "a"))
        self.assertFalse(simulate_nfa(nfa, "b"))
        self.assertFalse(simulate_nfa(nfa, ""))
        self.assertFalse(simulate_nfa(nfa, "aa"))

    def test_epsilon(self) -> None:
        """Epsilon: принимается только пустая строка."""
        nfa = self.builder.build(Epsilon())
        self.assertTrue(simulate_nfa(nfa, ""))
        self.assertFalse(simulate_nfa(nfa, "a"))

    def test_or(self) -> None:
        """Or: принимается одна из альтернатив."""
        nfa = self.builder.build(Or(Literal("a"), Literal("b")))
        self.assertTrue(simulate_nfa(nfa, "a"))
        self.assertTrue(simulate_nfa(nfa, "b"))
        self.assertFalse(simulate_nfa(nfa, "c"))
        self.assertFalse(simulate_nfa(nfa, ""))

    def test_concat(self) -> None:
        """Concat: порядок символов важен."""
        nfa = self.builder.build(Concat(Literal("a"), Literal("b")))
        self.assertTrue(simulate_nfa(nfa, "ab"))
        self.assertFalse(simulate_nfa(nfa, "a"))
        self.assertFalse(simulate_nfa(nfa, "b"))
        self.assertFalse(simulate_nfa(nfa, "ba"))

    def test_star(self) -> None:
        """Star: ноль и более повторов."""
        nfa = self.builder.build(Star(Literal("a")))
        self.assertTrue(simulate_nfa(nfa, ""))
        self.assertTrue(simulate_nfa(nfa, "a"))
        self.assertTrue(simulate_nfa(nfa, "aaa"))
        self.assertFalse(simulate_nfa(nfa, "b"))

    def test_plus(self) -> None:
        """Plus: один и более повторов."""
        nfa = self.builder.build(Plus(Literal("a")))
        self.assertFalse(simulate_nfa(nfa, ""))
        self.assertTrue(simulate_nfa(nfa, "a"))
        self.assertTrue(simulate_nfa(nfa, "aaa"))
        self.assertFalse(simulate_nfa(nfa, "b"))

    def test_char_range(self) -> None:
        """CharRange: принимаются символы из диапазона."""
        nfa = self.builder.build(CharRange([("a", "c")]))
        self.assertTrue(simulate_nfa(nfa, "a"))
        self.assertTrue(simulate_nfa(nfa, "b"))
        self.assertTrue(simulate_nfa(nfa, "c"))
        self.assertFalse(simulate_nfa(nfa, "d"))
        self.assertFalse(simulate_nfa(nfa, ""))

    def test_repeat_fixed(self) -> None:
        """Repeat {3}: строго три повтора."""
        nfa = self.builder.build(Repeat(Literal("a"), 3, 3))
        self.assertTrue(simulate_nfa(nfa, "aaa"))
        self.assertFalse(simulate_nfa(nfa, "aa"))
        self.assertFalse(simulate_nfa(nfa, "aaaa"))

    def test_repeat_range(self) -> None:
        """Repeat {2,4}: от двух до четырех повторов."""
        nfa = self.builder.build(Repeat(Literal("a"), 2, 4))
        self.assertFalse(simulate_nfa(nfa, "a"))
        self.assertTrue(simulate_nfa(nfa, "aa"))
        self.assertTrue(simulate_nfa(nfa, "aaa"))
        self.assertTrue(simulate_nfa(nfa, "aaaa"))
        self.assertFalse(simulate_nfa(nfa, "aaaaa"))

    def test_repeat_open_upper(self) -> None:
        """Repeat {2,}: неограниченный верх."""
        nfa = self.builder.build(Repeat(Literal("a"), 2, None))
        self.assertFalse(simulate_nfa(nfa, "a"))
        self.assertTrue(simulate_nfa(nfa, "aa"))
        self.assertTrue(simulate_nfa(nfa, "aaaaaaa"))

    def test_repeat_open_lower(self) -> None:
        """Repeat {,3}: до трех повторов включая ноль."""
        nfa = self.builder.build(Repeat(Literal("a"), 0, 3))
        self.assertTrue(simulate_nfa(nfa, ""))
        self.assertTrue(simulate_nfa(nfa, "a"))
        self.assertTrue(simulate_nfa(nfa, "aaa"))
        self.assertFalse(simulate_nfa(nfa, "aaaa"))

    def test_group(self) -> None:
        """Group: проставляются метки начала и конца группы."""
        nfa = self.builder.build(Group(Literal("a"), 1))
        self.assertTrue(simulate_nfa(nfa, "a"))
        self.assertEqual(nfa.start.group_start, 1)
        self.assertEqual(nfa.end.group_end, 1)

    def test_complex_expression_from_parser(self) -> None:
        """Проверка совместной работы парсера и построителя НКА."""
        ast = Parser("(a|b)*c").parse()
        nfa = self.builder.build(ast)
        self.assertTrue(simulate_nfa(nfa, "c"))
        self.assertTrue(simulate_nfa(nfa, "ac"))
        self.assertTrue(simulate_nfa(nfa, "bc"))
        self.assertTrue(simulate_nfa(nfa, "abc"))
        self.assertTrue(simulate_nfa(nfa, "ababc"))
        self.assertFalse(simulate_nfa(nfa, "ab"))
        self.assertFalse(simulate_nfa(nfa, ""))

    def test_epsilon_closure(self) -> None:
        """Проверяет достижимость по epsilon-цепочке."""
        s1 = NFAState()
        s2 = NFAState()
        s3 = NFAState()
        s1.add_transition(EPSILON, s2)
        s2.add_transition(EPSILON, s3)

        closure = epsilon_closure({s1})
        self.assertIn(s1, closure)
        self.assertIn(s2, closure)
        self.assertIn(s3, closure)

    def test_get_alphabet(self) -> None:
        """Алфавит содержит только обычные символы переходов."""
        nfa = self.builder.build(Or(Literal("a"), Literal("b")))
        alphabet = get_alphabet(nfa.start)
        self.assertIn("a", alphabet)
        self.assertIn("b", alphabet)
        self.assertNotIn(None, alphabet)


if __name__ == "__main__":
    unittest.main()
