"""Тесты парсера регулярных выражений."""

import unittest

from regex.ast_nodes import CharRange, Concat, Epsilon, Group, Literal, Lookahead, Or, Plus, Repeat, Star
from regex.parser import parse


class TestParser(unittest.TestCase):
    """Набор тестов для проверки построения AST."""

    def test_simple_literal(self) -> None:
        """Парсинг одного литерала."""
        self.assertEqual(parse("a"), Literal("a"))

    def test_or_expression(self) -> None:
        """Парсинг альтернативы."""
        self.assertEqual(parse("a|b"), Or(Literal("a"), Literal("b")))

    def test_concat_explicit(self) -> None:
        """Явная конкатенация через точку."""
        self.assertEqual(parse("a.b"), Concat(Literal("a"), Literal("b")))

    def test_concat_implicit(self) -> None:
        """Неявная конкатенация без точки."""
        self.assertEqual(parse("ab"), Concat(Literal("a"), Literal("b")))

    def test_star_variants(self) -> None:
        """Проверка обоих вариантов замыкания Клини."""
        self.assertEqual(parse("a*"), Star(Literal("a")))
        self.assertEqual(parse("a…"), Star(Literal("a")))

    def test_plus(self) -> None:
        """Позитивное замыкание."""
        self.assertEqual(parse("a+"), Plus(Literal("a")))

    def test_char_range(self) -> None:
        """Диапазоны символов в квадратных скобках."""
        self.assertEqual(parse("[a-z]"), CharRange([("a", "z")]))
        self.assertEqual(parse("[a-z0-9]"), CharRange([("a", "z"), ("0", "9")]))

    def test_repeat_quantifiers(self) -> None:
        """Квантификаторы повторов с границами."""
        self.assertEqual(parse("a{3,5}"), Repeat(Literal("a"), 3, 5))
        self.assertEqual(parse("a{3,}"), Repeat(Literal("a"), 3, None))
        self.assertEqual(parse("a{,5}"), Repeat(Literal("a"), 0, 5))
        self.assertEqual(parse("a{3}"), Repeat(Literal("a"), 3, 3))

    def test_capture_group(self) -> None:
        """Одна группа захвата с нумерацией."""
        self.assertEqual(parse("(ab)"), Group(Concat(Literal("a"), Literal("b")), 1))

    def test_nested_groups(self) -> None:
        """Вложенные группы нумеруются по закрытию (как в варианте задания)."""
        self.assertEqual(
            parse("((a)b)"),
            Group(Concat(Group(Literal("a"), 1), Literal("b")), 2),
        )

    def test_epsilon(self) -> None:
        """Символ '$' соответствует пустой строке."""
        self.assertEqual(parse("$"), Epsilon())

    def test_escaping(self) -> None:
        """Экранирование метасимволов через '%'."""
        self.assertEqual(parse("%|"), Literal("|"))
        self.assertEqual(parse("%%"), Literal("%"))
        self.assertEqual(parse("%*"), Literal("*"))

    def test_lookahead(self) -> None:
        """Прогностический оператор."""
        self.assertEqual(parse("a/b"), Lookahead(Literal("a"), Literal("b")))

    def test_complex_expression(self) -> None:
        """Комбинация группировки, альтернативы и конкатенации."""
        self.assertEqual(
            parse("(a|b)*c"),
            Concat(Star(Group(Or(Literal("a"), Literal("b")), 1)), Literal("c")),
        )

    def test_invalid_expressions(self) -> None:
        """Ошибочные выражения выбрасывают ValueError."""
        invalid_patterns = ["(a", "a{3", "[a-", "|a", "a{5,3}"]
        for pattern in invalid_patterns:
            with self.subTest(pattern=pattern):
                with self.assertRaises(ValueError):
                    parse(pattern)


if __name__ == "__main__":
    unittest.main()
