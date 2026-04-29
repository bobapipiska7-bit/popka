"""Узлы абстрактного синтаксического дерева регулярного выражения."""

from __future__ import annotations

from dataclasses import dataclass


class ASTNode:
    """Базовый класс для всех узлов AST."""


@dataclass(frozen=True)
class Literal(ASTNode):
    """Литерал: один символ алфавита."""

    char: str


@dataclass(frozen=True)
class Epsilon(ASTNode):
    """Пустая строка (метасимвол '$')."""


@dataclass(frozen=True)
class Or(ASTNode):
    """Операция альтернативы: r1|r2."""

    left: ASTNode
    right: ASTNode


@dataclass(frozen=True)
class Concat(ASTNode):
    """Операция конкатенации: r1r2 или r1.r2."""

    left: ASTNode
    right: ASTNode


@dataclass(frozen=True)
class Star(ASTNode):
    """Замыкание Клини: r* или r…."""

    expr: ASTNode


@dataclass(frozen=True)
class Plus(ASTNode):
    """Позитивное замыкание: r+."""

    expr: ASTNode


@dataclass(frozen=True)
class CharRange(ASTNode):
    """Диапазон символов: [a-z], [0-9], [a-zA-Z]."""

    ranges: list[tuple[str, str]]


@dataclass(frozen=True)
class Repeat(ASTNode):
    """Повтор в диапазоне: r{x,y}."""

    expr: ASTNode
    min_count: int
    max_count: int | None


@dataclass(frozen=True)
class Group(ASTNode):
    """Нумерованная группа захвата: (r)."""

    expr: ASTNode
    number: int


@dataclass(frozen=True)
class Lookahead(ASTNode):
    """Прогностический оператор: r1/r2."""

    expr: ASTNode
    lookahead: ASTNode
