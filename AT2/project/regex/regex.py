"""Основной класс регулярного выражения."""

from __future__ import annotations


class Regex:
    """
    Главный класс библиотеки.

    Точка входа для операций с регулярными выражениями.
    """

    def __init__(self, pattern: str):
        """
        Создаёт объект регулярного выражения.

        Параметры:
            pattern: строка с регулярным выражением (в синтаксисе задания)
        """
        self.pattern = pattern
        self._compiled = None  # CompiledRegex после вызова compile()
        self._nfa = None  # НКА для поиска с группами
        # Если True, объект задан только через ДКА (pattern может не быть валидным РВ).
        self._automaton_only = False

    def compile(self) -> "Regex":
        """
        Компилирует РВ в минимальный ДКА.

        РВ → НКА → ДКА → минимальный ДКА

        После вызова compile() объект хранит и НКА (для групп), и минимальный ДКА.
        """
        # Если объект уже содержит готовый ДКА (например, результат операций),
        # то повторная компиляция не нужна и может быть невозможна
        # (pattern может быть служебным, не парсится как РВ).
        if self._compiled is not None:
            return self

        from regex.parser import Parser
        from regex.nfa import NFABuilder
        from regex.dfa import DFABuilder
        from regex.minimizer import DFAMinimizer
        from regex.compiled import CompiledRegex

        class _CapturingNFABuilder(NFABuilder):
            """
            Расширение NFABuilder, которое поддерживает несколько меток групп
            на одном NFA-состоянии (нужно для вложенных групп).
            """

            def _build_group(self, node):  # type: ignore[override]
                expr_nfa = self.build(node.expr)

                def add_marker(state, attr_list: str, attr_single: str, num: int) -> None:
                    lst = getattr(state, attr_list, None)
                    if lst is None:
                        lst = []
                        setattr(state, attr_list, lst)
                    if num not in lst:
                        lst.append(num)
                    if getattr(state, attr_single, None) is None:
                        setattr(state, attr_single, num)

                add_marker(expr_nfa.start, "group_starts", "group_start", node.number)
                add_marker(expr_nfa.end, "group_ends", "group_end", node.number)
                return expr_nfa

        ast = Parser(self.pattern).parse()
        ast = self._renumber_groups_by_opening(ast)
        nfa = _CapturingNFABuilder().build(ast)

        # Сохраняем НКА для поиска с группами захвата
        self._nfa = nfa

        dfa = DFABuilder().build(nfa)
        min_dfa = DFAMinimizer().minimize(dfa)
        self._compiled = CompiledRegex(min_dfa, self.pattern)

        return self

    def _get_nfa(self):
        """Возвращает НКА, строя его если нужно."""
        if self._automaton_only:
            raise ValueError("НКА недоступен: объект задан только через ДКА.")
        if self._nfa is None:
            from regex.parser import Parser
            from regex.nfa import NFABuilder

            class _CapturingNFABuilder(NFABuilder):
                """
                Расширение NFABuilder, которое поддерживает несколько меток групп
                на одном NFA-состоянии (нужно для вложенных групп).
                """

                def _build_group(self, node):  # type: ignore[override]
                    expr_nfa = self.build(node.expr)

                    def add_marker(state, attr_list: str, attr_single: str, num: int) -> None:
                        lst = getattr(state, attr_list, None)
                        if lst is None:
                            lst = []
                            setattr(state, attr_list, lst)
                        if num not in lst:
                            lst.append(num)
                        if getattr(state, attr_single, None) is None:
                            setattr(state, attr_single, num)

                    add_marker(expr_nfa.start, "group_starts", "group_start", node.number)
                    add_marker(expr_nfa.end, "group_ends", "group_end", node.number)
                    return expr_nfa

            ast = Parser(self.pattern).parse()
            ast = self._renumber_groups_by_opening(ast)
            self._nfa = _CapturingNFABuilder().build(ast)
        return self._nfa

    def _renumber_groups_by_opening(self, ast):
        """
        Перенумеровывает группы захвата в порядке открытия скобок.

        Парсер текущего проекта присваивает номер при закрытии ')',
        то есть вложенные группы получают меньшие номера.

        По требованиям этого этапа (и тестам) группа 1 должна соответствовать
        первой открывающей скобке слева направо, поэтому выполняем перенумерацию
        на копии AST, не изменяя код парсера.
        """
        from dataclasses import replace
        from regex.ast_nodes import Concat, Group, Lookahead, Or, Plus, Repeat, Star

        counter = 0

        def visit(node):
            nonlocal counter
            if isinstance(node, Group):
                counter += 1
                num = counter
                new_expr = visit(node.expr)
                return replace(node, expr=new_expr, number=num)
            if isinstance(node, Or) or isinstance(node, Concat):
                new_left = visit(node.left)
                new_right = visit(node.right)
                return replace(node, left=new_left, right=new_right)
            if isinstance(node, Star) or isinstance(node, Plus):
                new_expr = visit(node.expr)
                return replace(node, expr=new_expr)
            if isinstance(node, Repeat):
                new_expr = visit(node.expr)
                return replace(node, expr=new_expr)
            if isinstance(node, Lookahead):
                new_expr = visit(node.expr)
                new_lookahead = visit(node.lookahead)
                return replace(node, expr=new_expr, lookahead=new_lookahead)
            # Literal / Epsilon / CharRange и др. листовые узлы не требуют обработки.
            return node

        return visit(ast)

    def _get_compiled(self):
        """Возвращает скомпилированный ДКА, строя его если нужно."""
        if self._compiled is None:
            self.compile()
        return self._compiled

    def search(self, string: str, groups: bool = False):
        """
        Ищет ПЕРВОЕ вхождение подстроки в строке.

        Алгоритм:
        - Перебираем все стартовые позиции 0..len(string)
        - Для каждой позиции ищем самое длинное совпадение, начинающееся там
        - Возвращаем первое найденное

        Параметры:
            string: строка для поиска
            groups: если True — возвращает Match; если False — (start, end) или None

        Возвращает:
            - если groups=False: (start, end) или None
            - если groups=True: Match или None
        """
        # 1) Пытаемся использовать НКА (нужно для groups и корректного поведения search),
        # если это не “automaton-only” объект.
        # Для объектов, полученных из операций над ДКА, pattern может не парситься,
        # поэтому делаем fallback на ДКА.
        if not self._automaton_only:
            try:
                nfa = self._get_nfa()
                from regex.match import simulate_nfa_with_groups

                for start_pos in range(len(string) + 1):
                    match = simulate_nfa_with_groups(nfa, string, start_pos)
                    if match is not None:
                        return match if groups else (match.start, match.end)
                return None
            except Exception:
                if groups:
                    raise

        # 2) Fallback: поиск по ДКА (для результатов операций).
        compiled = self._get_compiled()
        dfa = compiled.dfa

        from regex.operations import _find_trap_state

        trap = _find_trap_state(dfa)

        # Для ДКА-режима избегаем пустых совпадений на непустых строках:
        # иначе complement() почти всегда будет совпадать с "" в начале.
        allow_empty = len(string) == 0

        for start_pos in range(len(string) + 1):
            current = dfa.start
            best_end: int | None = start_pos if (allow_empty and current.is_final) else None

            pos = start_pos
            while pos < len(string):
                ch = string[pos]
                nxt = current.transitions.get(ch)
                if nxt is None:
                    if trap is None:
                        break
                    nxt = trap
                current = nxt
                pos += 1
                if current.is_final:
                    best_end = pos

            if best_end is not None:
                return (start_pos, best_end)

        return None

    def complement(self) -> "Regex":
        """
        Строит дополнение языка.

        Работает через ДКА, поэтому при поиске используется ДКА-режим (без групп).
        """
        from regex.compiled import CompiledRegex
        from regex.minimizer import DFAMinimizer
        from regex.operations import complement

        compiled = self._get_compiled()
        comp_dfa = complement(compiled.dfa)
        min_dfa = DFAMinimizer().minimize(comp_dfa)

        result = Regex(f"complement({self.pattern})")
        result._compiled = CompiledRegex(min_dfa, result.pattern)
        result._nfa = None
        result._automaton_only = True
        return result

    def difference(self, other: "Regex") -> "Regex":
        """
        Строит разность языков: self \\ other.

        Оба выражения при необходимости компилируются автоматически.
        """
        from regex.compiled import CompiledRegex
        from regex.minimizer import DFAMinimizer
        from regex.operations import difference

        dfa1 = self._get_compiled().dfa
        dfa2 = other._get_compiled().dfa

        diff_dfa = difference(dfa1, dfa2)
        min_dfa = DFAMinimizer().minimize(diff_dfa)

        result = Regex(f"({self.pattern})\\({other.pattern})")
        result._compiled = CompiledRegex(min_dfa, result.pattern)
        result._nfa = None
        result._automaton_only = True
        return result

    def restore(self) -> str:
        """
        Восстанавливает регулярное выражение из скомпилированного ДКА методом K-пути.
        """
        from regex.operations import restore

        compiled = self._get_compiled()
        return restore(compiled.dfa)

    def __repr__(self) -> str:
        """Короткое строковое представление."""
        compiled = "скомпилировано" if self._compiled else "не скомпилировано"
        return f"Regex(pattern='{self.pattern}', {compiled})"
