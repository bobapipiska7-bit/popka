"""Компиляция регулярного выражения в минимальный ДКА."""

from __future__ import annotations

from regex.dfa import DFA, DFABuilder
from regex.minimizer import DFAMinimizer
from regex.nfa import NFABuilder
from regex.parser import Parser


class CompiledRegex:
    """Скомпилированное регулярное выражение поверх минимального ДКА."""

    def __init__(self, dfa: DFA, pattern: str):
        """Сохраняет минимальный ДКА и исходный шаблон."""
        self.dfa = dfa
        self.pattern = pattern

    def accepts(self, string: str) -> bool:
        """Проверяет, принимает ли выражение строку целиком."""
        return self.dfa.accepts(string)

    def __repr__(self) -> str:
        """Возвращает краткое строковое представление объекта."""
        return f"CompiledRegex(pattern='{self.pattern}', states={len(self.dfa.states)})"


def compile_regex(pattern: str) -> CompiledRegex:
    """Компилирует РВ в минимальный ДКА по цепочке AST→НКА→ДКА→minDFA."""
    ast = Parser(pattern).parse()
    nfa = NFABuilder().build(ast)
    dfa = DFABuilder().build(nfa)
    min_dfa = DFAMinimizer().minimize(dfa)
    return CompiledRegex(min_dfa, pattern)
