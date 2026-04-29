"""Построение детерминированного автомата из НКА."""

from __future__ import annotations

from regex.nfa import NFA, epsilon_closure, get_alphabet, move


class DFAState:
    """Состояние детерминированного конечного автомата."""

    _counter = 0

    def __init__(self, nfa_states: frozenset):
        """Создает состояние ДКА как множество состояний НКА."""
        self.id = DFAState._counter
        DFAState._counter += 1
        self.nfa_states: frozenset = nfa_states
        self.transitions: dict[str, "DFAState"] = {}
        self.is_final: bool = False
        self.is_start: bool = False

    def add_transition(self, symbol: str, state: "DFAState") -> None:
        """Добавляет переход по символу в другое состояние ДКА."""
        self.transitions[symbol] = state

    def __repr__(self) -> str:
        """Возвращает строковое представление состояния."""
        return f"DFAState(id={self.id}, final={self.is_final})"

    def __hash__(self) -> int:
        """Позволяет использовать состояние в множествах и словарях."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Сравнивает состояния ДКА по уникальному id."""
        return isinstance(other, DFAState) and self.id == other.id


class DFA:
    """Детерминированный конечный автомат."""

    def __init__(self, start: DFAState, states: list[DFAState], alphabet: set[str]):
        """Сохраняет стартовое состояние, список состояний и алфавит."""
        self.start = start
        self.states = states
        self.alphabet = alphabet

    @property
    def final_states(self) -> list[DFAState]:
        """Возвращает список финальных состояний."""
        return [state for state in self.states if state.is_final]

    def accepts(self, string: str) -> bool:
        """Проверяет, принимает ли автомат строку целиком."""
        current = self.start
        for char in string:
            if char not in current.transitions:
                return False
            current = current.transitions[char]
        return current.is_final

    def __repr__(self) -> str:
        """Возвращает строковое представление ДКА."""
        return f"DFA(states={len(self.states)}, alphabet={self.alphabet})"


class DFABuilder:
    """Строит ДКА из НКА алгоритмом subset construction."""

    def build(self, nfa: NFA) -> DFA:
        """Преобразует НКА в ДКА по методу множеств состояний."""
        alphabet = get_alphabet(nfa.start)

        start_closure = frozenset(epsilon_closure({nfa.start}))
        start_dfa = DFAState(start_closure)
        start_dfa.is_start = True
        start_dfa.is_final = any(state.is_final for state in start_closure)

        dfa_states: dict[frozenset, DFAState] = {start_closure: start_dfa}
        queue: list[DFAState] = [start_dfa]
        all_states: list[DFAState] = [start_dfa]

        while queue:
            current_dfa = queue.pop(0)
            for symbol in alphabet:
                moved = move(set(current_dfa.nfa_states), symbol)
                if not moved:
                    continue

                closure = frozenset(epsilon_closure(moved))
                if not closure:
                    continue

                if closure not in dfa_states:
                    new_state = DFAState(closure)
                    new_state.is_final = any(state.is_final for state in closure)
                    dfa_states[closure] = new_state
                    all_states.append(new_state)
                    queue.append(new_state)

                current_dfa.add_transition(symbol, dfa_states[closure])

        return DFA(start=start_dfa, states=all_states, alphabet=alphabet)
