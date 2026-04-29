"""Рекурсивный парсер регулярных выражений в AST."""

from __future__ import annotations

from .ast_nodes import ASTNode, CharRange, Concat, Epsilon, Group, Literal, Lookahead, Or, Plus, Repeat, Star


class Parser:
    """Парсер регулярных выражений в узлы AST."""

    def __init__(self, pattern: str):
        """Сохраняет шаблон и инициализирует состояние парсера."""
        self.pattern = pattern
        self.pos = 0
        self.group_counter = 0

    def parse(self) -> ASTNode:
        """Точка входа: разбирает выражение целиком и возвращает AST."""
        ast = self._parse_expression()
        if self.pos != len(self.pattern):
            char = self.pattern[self.pos]
            raise ValueError(f"Неожиданный символ '{char}' на позиции {self.pos}")
        return ast

    def _parse_expression(self) -> ASTNode:
        """expression → concat ('|' concat)*."""
        left = self._parse_concat()
        while self._current_char() == "|":
            self._consume("|")
            right = self._parse_concat()
            left = Or(left=left, right=right)
        return left

    def _parse_concat(self) -> ASTNode:
        """concat → repeat ('.'? repeat)*."""
        if not self._is_atom_start():
            current = self._current_char()
            shown = "конец выражения" if current is None else f"'{current}'"
            raise ValueError(f"Ожидалось начало выражения на позиции {self.pos}, получено {shown}")

        left = self._parse_repeat()
        while True:
            if self._current_char() == ".":
                self._consume(".")
                right = self._parse_repeat()
                left = Concat(left=left, right=right)
                continue
            if self._is_atom_start():
                right = self._parse_repeat()
                left = Concat(left=left, right=right)
                continue
            break
        return left

    def _parse_repeat(self) -> ASTNode:
        """repeat → atom postfix*."""
        node = self._parse_atom()
        if self._current_char() == "/":
            self._consume("/")
            if not self._is_atom_start():
                raise ValueError(f"Ожидалось выражение после '/' на позиции {self.pos}")
            lookahead = self._parse_atom()
            node = Lookahead(expr=node, lookahead=lookahead)

        while True:
            current = self._current_char()
            if current in ("*", "…"):
                self._consume()
                node = Star(expr=node)
                continue
            if current == "+":
                self._consume("+")
                node = Plus(expr=node)
                continue
            if current == "{":
                node = self._parse_repeat_quantifier(node)
                continue
            break
        return node

    def _parse_atom(self) -> ASTNode:
        """atom → group | range | epsilon | escaped | char."""
        current = self._current_char()
        if current is None:
            raise ValueError(f"Неожиданный конец выражения на позиции {self.pos}")
        if current == "(":
            return self._parse_group()
        if current == "[":
            return self._parse_char_range()
        if current == "$":
            self._consume("$")
            return Epsilon()
        if current == "%":
            self._consume("%")
            escaped = self._current_char()
            if escaped is None:
                raise ValueError(f"Ожидался символ после '%' на позиции {self.pos}")
            self._consume()
            return Literal(char=escaped)
        if current in {"|", ")", "]", "}", ".", "*", "+", "/", "{"}:
            raise ValueError(f"Неожиданный символ '{current}' на позиции {self.pos}")
        self._consume()
        return Literal(char=current)

    def _parse_group(self) -> ASTNode:
        """( expression ) с нумерацией групп."""
        self._consume("(")
        expr = self._parse_expression()
        if self._current_char() != ")":
            raise ValueError(f"Ожидалась ')' на позиции {self.pos}")
        self._consume(")")
        # Номер присваивается при закрытии группы.
        self.group_counter += 1
        return Group(expr=expr, number=self.group_counter)

    def _parse_char_range(self) -> ASTNode:
        """[ range_expr ] с поддержкой диапазонов и одиночных символов."""
        self._consume("[")
        ranges: list[tuple[str, str]] = []
        while True:
            current = self._current_char()
            if current is None:
                raise ValueError(f"Ожидалась ']' для диапазона на позиции {self.pos}")
            if current == "]":
                break
            start = self._parse_range_char()
            if self._current_char() == "-":
                self._consume("-")
                end_current = self._current_char()
                if end_current in (None, "]"):
                    raise ValueError(f"Некорректный диапазон в позиции {self.pos}")
                end = self._parse_range_char()
                if start > end:
                    raise ValueError(f"Некорректный диапазон '{start}-{end}' на позиции {self.pos}")
                ranges.append((start, end))
            else:
                ranges.append((start, start))
        self._consume("]")
        if not ranges:
            raise ValueError("Пустой диапазон символов [] недопустим")
        return CharRange(ranges=ranges)

    def _parse_range_char(self) -> str:
        """Читает один символ внутри [...] с учетом экранирования '%'."""
        current = self._current_char()
        if current is None:
            raise ValueError(f"Неожиданный конец диапазона на позиции {self.pos}")
        if current == "%":
            self._consume("%")
            escaped = self._current_char()
            if escaped is None:
                raise ValueError(f"Ожидался символ после '%' в диапазоне на позиции {self.pos}")
            self._consume()
            return escaped
        if current == "[":
            raise ValueError(f"Неожиданный символ '[' внутри диапазона на позиции {self.pos}")
        self._consume()
        return current

    def _parse_repeat_quantifier(self, expr: ASTNode) -> ASTNode:
        """{ x, y } или { x } с поддержкой открытых границ."""
        self._consume("{")
        min_text = self._consume_digits()
        if self._current_char() == "}":
            self._consume("}")
            if min_text == "":
                raise ValueError(f"Ожидалось число в repeat на позиции {self.pos}")
            count = int(min_text)
            return Repeat(expr=expr, min_count=count, max_count=count)

        self._consume(",")
        max_text = self._consume_digits()
        self._consume("}")

        min_count = int(min_text) if min_text else 0
        max_count = int(max_text) if max_text else None
        if max_count is not None and min_count > max_count:
            raise ValueError(f"Некорректный repeat: min={min_count} > max={max_count}")
        return Repeat(expr=expr, min_count=min_count, max_count=max_count)

    def _consume_digits(self) -> str:
        """Считывает последовательность цифр (возможно пустую)."""
        start = self.pos
        while (char := self._current_char()) is not None and char.isdigit():
            self._consume()
        return self.pattern[start:self.pos]

    def _current_char(self) -> str | None:
        """Возвращает текущий символ или None при конце строки."""
        if self.pos >= len(self.pattern):
            return None
        return self.pattern[self.pos]

    def _consume(self, expected: str | None = None) -> str:
        """Съедает текущий символ, при необходимости проверяя expected."""
        current = self._current_char()
        if current is None:
            raise ValueError(f"Неожиданный конец выражения на позиции {self.pos}")
        if expected is not None and current != expected:
            raise ValueError(f"Ожидался символ '{expected}' на позиции {self.pos}, получен '{current}'")
        self.pos += 1
        return current

    def _is_atom_start(self) -> bool:
        """Проверяет, может ли текущая позиция начинать новый atom."""
        current = self._current_char()
        if current is None:
            return False
        if current in {"|", ")", "]", "}"}:
            return False
        if current in {".", "*", "+", "/"}:
            return False
        if current == "{":
            return False
        return True


def parse(pattern: str) -> ASTNode:
    """Удобная функция для парсинга регулярного выражения."""
    return Parser(pattern).parse()
