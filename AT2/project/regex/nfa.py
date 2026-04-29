"""Построение НКА из AST по алгоритму Томпсона."""

from __future__ import annotations

from regex.ast_nodes import ASTNode, CharRange, Concat, Epsilon, Group, Literal, Lookahead, Or, Plus, Repeat, Star

EPSILON = None


class NFAState:
    """Состояние недетерминированного конечного автомата."""

    _counter = 0

    def __init__(self) -> None:
        """Создает состояние с уникальным id и пустыми переходами."""
        self.id = NFAState._counter
        NFAState._counter += 1
        self.transitions: dict[str | None, list["NFAState"]] = {}
        self.group_start: int | None = None
        self.group_end: int | None = None
        self.lookahead_nfa: "NFA | None" = None
        self.is_final: bool = False

    def add_transition(self, symbol: str | None, state: "NFAState") -> None:
        """Добавляет переход по символу (или epsilon) в другое состояние."""
        if symbol not in self.transitions:
            self.transitions[symbol] = []
        self.transitions[symbol].append(state)

    def __repr__(self) -> str:
        """Возвращает строковое представление состояния."""
        return f"NFAState(id={self.id})"

    def __hash__(self) -> int:
        """Позволяет использовать состояние в множествах и как ключ словаря."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Сравнивает состояния по идентификатору."""
        return isinstance(other, NFAState) and self.id == other.id


class NFA:
    """НКА с ровно одним конечным состоянием."""

    def __init__(self, start: NFAState, end: NFAState) -> None:
        """Сохраняет стартовое и конечное состояния автомата."""
        self.start = start
        self.end = end

    def __repr__(self) -> str:
        """Возвращает строковое представление НКА."""
        return f"NFA(start={self.start}, end={self.end})"


class NFABuilder:
    """Строит НКА из AST по алгоритму Томпсона."""

    def build(self, node: ASTNode) -> NFA:
        """Точка входа: выбирает обработчик по типу узла AST."""
        if isinstance(node, Literal):
            return self._build_literal(node)
        if isinstance(node, Epsilon):
            return self._build_epsilon(node)
        if isinstance(node, Or):
            return self._build_or(node)
        if isinstance(node, Concat):
            return self._build_concat(node)
        if isinstance(node, Star):
            return self._build_star(node)
        if isinstance(node, Plus):
            return self._build_plus(node)
        if isinstance(node, CharRange):
            return self._build_char_range(node)
        if isinstance(node, Repeat):
            return self._build_repeat(node)
        if isinstance(node, Group):
            return self._build_group(node)
        if isinstance(node, Lookahead):
            return self._build_lookahead(node)
        raise ValueError(f"Неподдерживаемый тип AST-узла: {type(node).__name__}")

    def _build_literal(self, node: Literal) -> NFA:
        """Строит НКА для одного литерала."""
        start = NFAState()
        end = NFAState()
        end.is_final = True
        start.add_transition(node.char, end)
        return NFA(start, end)

    def _build_epsilon(self, node: Epsilon) -> NFA:
        """Строит НКА для пустой строки."""
        _ = node
        start = NFAState()
        end = NFAState()
        end.is_final = True
        start.add_transition(EPSILON, end)
        return NFA(start, end)

    def _build_or(self, node: Or) -> NFA:
        """Строит НКА для альтернативы r1|r2."""
        left_nfa = self.build(node.left)
        right_nfa = self.build(node.right)
        return self._merge_or(left_nfa, right_nfa)

    def _build_concat(self, node: Concat) -> NFA:
        """Строит НКА для конкатенации r1r2."""
        left_nfa = self.build(node.left)
        right_nfa = self.build(node.right)
        left_nfa.end.is_final = False
        left_nfa.end.add_transition(EPSILON, right_nfa.start)
        return NFA(left_nfa.start, right_nfa.end)

    def _build_star(self, node: Star) -> NFA:
        """Строит НКА для замыкания Клини r*."""
        expr_nfa = self.build(node.expr)
        expr_nfa.end.is_final = False

        start = NFAState()
        end = NFAState()
        end.is_final = True

        start.add_transition(EPSILON, expr_nfa.start)
        start.add_transition(EPSILON, end)
        expr_nfa.end.add_transition(EPSILON, expr_nfa.start)
        expr_nfa.end.add_transition(EPSILON, end)
        return NFA(start, end)

    def _build_plus(self, node: Plus) -> NFA:
        """Строит НКА для позитивного замыкания r+."""
        expr_nfa = self.build(node.expr)
        expr_nfa.end.is_final = False

        start = NFAState()
        end = NFAState()
        end.is_final = True

        start.add_transition(EPSILON, expr_nfa.start)
        expr_nfa.end.add_transition(EPSILON, expr_nfa.start)
        expr_nfa.end.add_transition(EPSILON, end)
        return NFA(start, end)

    def _build_char_range(self, node: CharRange) -> NFA:
        """Строит НКА для диапазона символов, разворачивая его в OR."""
        chars: list[str] = []
        for from_char, to_char in node.ranges:
            for code in range(ord(from_char), ord(to_char) + 1):
                chars.append(chr(code))

        if not chars:
            raise ValueError("Пустой диапазон символов")

        result = self._build_literal_char(chars[0])
        for char in chars[1:]:
            result = self._merge_or(result, self._build_literal_char(char))
        return result

    def _build_literal_char(self, char: str) -> NFA:
        """Строит НКА для одного символа без AST-обертки."""
        start = NFAState()
        end = NFAState()
        end.is_final = True
        start.add_transition(char, end)
        return NFA(start, end)

    def _merge_or(self, left_nfa: NFA, right_nfa: NFA) -> NFA:
        """Объединяет два НКА в один через альтернативу."""
        start = NFAState()
        end = NFAState()
        end.is_final = True

        left_nfa.end.is_final = False
        right_nfa.end.is_final = False
        start.add_transition(EPSILON, left_nfa.start)
        start.add_transition(EPSILON, right_nfa.start)
        left_nfa.end.add_transition(EPSILON, end)
        right_nfa.end.add_transition(EPSILON, end)
        return NFA(start, end)

    def _build_repeat(self, node: Repeat) -> NFA:
        """Строит НКА для повторов r{x,y}, r{x,}, r{,y}, r{x}."""
        min_count = node.min_count
        max_count = node.max_count

        if min_count < 0:
            raise ValueError("min_count не может быть отрицательным")
        if max_count is not None and min_count > max_count:
            raise ValueError("min_count не может быть больше max_count")

        parts: list[NFA] = []
        for _ in range(min_count):
            parts.append(self.build(node.expr))

        if max_count is None:
            parts.append(self._build_star(Star(node.expr)))
        else:
            for _ in range(max_count - min_count):
                optional = self._merge_or(self.build(node.expr), self._build_epsilon(Epsilon()))
                parts.append(optional)

        if not parts:
            return self._build_epsilon(Epsilon())

        result = parts[0]
        for part in parts[1:]:
            result.end.is_final = False
            result.end.add_transition(EPSILON, part.start)
            result = NFA(result.start, part.end)

        result.end.is_final = True
        return result

    def _build_group(self, node: Group) -> NFA:
        """Строит НКА для группы и проставляет маркеры ее границ."""
        expr_nfa = self.build(node.expr)
        expr_nfa.start.group_start = node.number
        expr_nfa.end.group_end = node.number
        return expr_nfa

    def _build_lookahead(self, node: Lookahead) -> NFA:
        """Строит НКА для lookahead и сохраняет ссылку на проверку хвоста."""
        expr_nfa = self.build(node.expr)
        lookahead_nfa = self.build(node.lookahead)
        expr_nfa.end.lookahead_nfa = lookahead_nfa
        return expr_nfa


def epsilon_closure(states: set[NFAState]) -> set[NFAState]:
    """Возвращает epsilon-замыкание для заданного множества состояний."""
    closure = set(states)
    stack = list(states)

    while stack:
        state = stack.pop()
        for next_state in state.transitions.get(EPSILON, []):
            if next_state not in closure:
                closure.add(next_state)
                stack.append(next_state)
    return closure


def move(states: set[NFAState], symbol: str) -> set[NFAState]:
    """Возвращает состояния, достижимые по символу symbol без epsilon."""
    result: set[NFAState] = set()
    for state in states:
        for next_state in state.transitions.get(symbol, []):
            result.add(next_state)
    return result


def get_alphabet(start_state: NFAState) -> set[str]:
    """Собирает алфавит НКА (все символы переходов кроме epsilon)."""
    alphabet: set[str] = set()
    visited: set[NFAState] = set()
    stack = [start_state]

    while stack:
        state = stack.pop()
        if state in visited:
            continue
        visited.add(state)

        for symbol, next_states in state.transitions.items():
            if symbol is not None:
                alphabet.add(symbol)
            for next_state in next_states:
                if next_state not in visited:
                    stack.append(next_state)
    return alphabet


def get_all_states(start_state: NFAState) -> set[NFAState]:
    """Возвращает множество всех состояний, достижимых из start_state."""
    visited: set[NFAState] = set()
    stack = [start_state]

    while stack:
        state = stack.pop()
        if state in visited:
            continue
        visited.add(state)
        for next_states in state.transitions.values():
            for next_state in next_states:
                if next_state not in visited:
                    stack.append(next_state)
    return visited
