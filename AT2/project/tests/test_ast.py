"""Тесты узлов AST."""

import unittest

from regex.ast_nodes import CharRange, Concat, Epsilon, Group, Literal, Lookahead, Or, Plus, Repeat, Star


class TestASTNodes(unittest.TestCase):
    """Проверяет базовые свойства узлов AST."""

    def test_literal_node(self) -> None:
        """Литерал хранит символ."""
        node = Literal("a")
        self.assertEqual(node.char, "a")

    def test_binary_nodes(self) -> None:
        """Бинарные узлы сохраняют левое и правое поддерево."""
        left = Literal("a")
        right = Literal("b")
        self.assertEqual(Or(left, right), Or(left, right))
        self.assertEqual(Concat(left, right), Concat(left, right))
        self.assertEqual(Lookahead(left, right), Lookahead(left, right))

    def test_unary_nodes(self) -> None:
        """Унарные узлы оборачивают выражение."""
        expr = Literal("a")
        self.assertEqual(Star(expr), Star(expr))
        self.assertEqual(Plus(expr), Plus(expr))
        self.assertEqual(Repeat(expr, 1, 3), Repeat(expr, 1, 3))
        self.assertEqual(Group(expr, 1), Group(expr, 1))

    def test_other_nodes(self) -> None:
        """Дополнительные узлы создаются корректно."""
        self.assertEqual(Epsilon(), Epsilon())
        self.assertEqual(CharRange([("a", "z")]), CharRange([("a", "z")]))


if __name__ == "__main__":
    unittest.main()
