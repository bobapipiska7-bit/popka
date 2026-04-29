"""
Модуль операций над регулярными выражениями.

Содержит операции над языками, заданными детерминированными автоматами:
- дополнение (complement)
- пересечение (intersection)
- разность (difference)

А также восстановление регулярного выражения из ДКА методом K-пути (Клини).
"""

from __future__ import annotations

from regex.dfa import DFA, DFAState


def _clone_dfa(dfa: DFA) -> DFA:
    """
    Делает глубокую копию ДКА (с новыми объектами состояний).

    Это нужно, чтобы операции не модифицировали исходные автоматы
    (исходные объекты могут использоваться в других местах).
    """
    # Сбрасывать счётчик не будем: id в копии не важны для корректности,
    # но должны быть уникальными внутри копии.
    old_to_new: dict[DFAState, DFAState] = {}
    for st in dfa.states:
        new_st = DFAState(frozenset())
        new_st.is_final = st.is_final
        new_st.is_start = st.is_start
        old_to_new[st] = new_st

    for st in dfa.states:
        new_st = old_to_new[st]
        for sym, tgt in st.transitions.items():
            new_st.add_transition(sym, old_to_new[tgt])

    new_start = old_to_new[dfa.start]
    return DFA(start=new_start, states=list(old_to_new.values()), alphabet=set(dfa.alphabet))


def _find_trap_state(dfa: DFA) -> DFAState | None:
    """
    Пытается найти trap-состояние в ДКА.

    Trap в нашем подходе:
    - имеет переходы по всем символам алфавита
    - и по каждому символу ведёт в себя
    """
    if not dfa.alphabet:
        return None
    for st in dfa.states:
        ok = True
        for sym in dfa.alphabet:
            if st.transitions.get(sym) is not st:
                ok = False
                break
        if ok:
            return st
    return None


def _make_total(dfa: DFA, alphabet: set[str]) -> DFA:
    """
    Делает ДКА полным на заданном алфавите: добавляет trap и заполняет переходы.

    Возвращает НОВЫЙ ДКА (копию).
    """
    dfa = _clone_dfa(dfa)
    dfa.alphabet = set(alphabet)

    trap = DFAState(frozenset())
    trap.is_final = False
    trap.is_start = False
    for sym in alphabet:
        trap.add_transition(sym, trap)

    trap_needed = False
    for st in dfa.states:
        for sym in alphabet:
            if sym not in st.transitions:
                st.add_transition(sym, trap)
                trap_needed = True

    states = list(dfa.states)
    if trap_needed:
        states.append(trap)

    return DFA(start=dfa.start, states=states, alphabet=set(alphabet))


def complement(dfa: DFA) -> DFA:
    """
    Строит дополнение языка заданного ДКА.

    Алгоритм:
    1) Делаем ДКА полным (добавляем trap-состояние для отсутствующих переходов).
    2) Инвертируем финальные и нефинальные состояния.
    """
    # Полнота нужна для корректного дополнения.
    dfa = _make_total(dfa, set(dfa.alphabet))
    new_states = list(dfa.states)

    # Шаг 2: инвертируем финальность
    for state in new_states:
        state.is_final = not state.is_final

    return DFA(start=dfa.start, states=new_states, alphabet=set(dfa.alphabet))


def intersection(dfa1: DFA, dfa2: DFA) -> DFA:
    """
    Строит пересечение двух ДКА через декартово произведение.

    Состояние результата = пара (s1, s2).
    Финальное состояние = оба состояния финальные.

    Важно:
    - Алфавит берём общий (объединение).
    - Переходы могут быть частичными (в исходных ДКА), поэтому если у
      одного автомата нет перехода по символу — переход в пересечении отсутствует.
    """
    alphabet = set(dfa1.alphabet) | set(dfa2.alphabet)

    # В пересечении нужно, чтобы оба автомата были полными на общем алфавите.
    dfa1 = _make_total(dfa1, alphabet)
    dfa2 = _make_total(dfa2, alphabet)

    state_map: dict[tuple[int, int], DFAState] = {}
    created_states: list[DFAState] = []
    queue: list[tuple[DFAState, DFAState]] = []

    def get_or_create(s1: DFAState, s2: DFAState) -> DFAState:
        key = (s1.id, s2.id)
        if key not in state_map:
            ns = DFAState(frozenset())
            ns.is_final = s1.is_final and s2.is_final
            state_map[key] = ns
            created_states.append(ns)
            queue.append((s1, s2))
        return state_map[key]

    start = get_or_create(dfa1.start, dfa2.start)
    start.is_start = True

    visited: set[tuple[int, int]] = set()
    while queue:
        s1, s2 = queue.pop(0)
        key = (s1.id, s2.id)
        if key in visited:
            continue
        visited.add(key)

        cur = state_map[key]
        for sym in alphabet:
            n1 = s1.transitions[sym]
            n2 = s2.transitions[sym]
            nxt = get_or_create(n1, n2)
            cur.add_transition(sym, nxt)

    return DFA(start=start, states=created_states, alphabet=alphabet)


def difference(dfa1: DFA, dfa2: DFA) -> DFA:
    """
    Строит разность языков L1 \\ L2.

    L1 \\ L2 = L1 ∩ complement(L2)
    """
    alphabet = set(dfa1.alphabet) | set(dfa2.alphabet)
    dfa1_total = _make_total(dfa1, alphabet)
    dfa2_total = _make_total(dfa2, alphabet)
    comp_dfa2 = complement(dfa2_total)
    return intersection(dfa1_total, comp_dfa2)


def restore(dfa: DFA) -> str:
    """
    Восстанавливает регулярное выражение из ДКА методом K-пути (метод Клини).

    Возвращает строку регулярного выражения в синтаксисе проекта:
    - конкатенация через '.'
    - ε через '$'
    - экранирование метасимволов через '%'
    """
    states = list(dfa.states)
    n = len(states)
    if n == 0:
        return "∅"

    # Нумеруем состояния
    state_index = {s: i for i, s in enumerate(states)}
    start_idx = state_index[dfa.start]

    # R[i][j] = РВ для всех путей из i в j, используя промежуточные состояния ≤ k
    R: list[list[str | None]] = [[None for _ in range(n)] for _ in range(n)]

    # База: прямые переходы
    for i, st in enumerate(states):
        for symbol, next_st in st.transitions.items():
            j = state_index[next_st]
            esc = _escape(symbol)
            R[i][j] = _or(R[i][j], esc)

    # Добавляем ε для i==i
    for i in range(n):
        R[i][i] = _or(R[i][i], "$")

    # Итерации по k
    for k in range(n):
        new_R: list[list[str | None]] = [[None for _ in range(n)] for _ in range(n)]
        for i in range(n):
            for j in range(n):
                r_ij = R[i][j]
                r_ik = R[i][k]
                r_kk = R[k][k]
                r_kj = R[k][j]

                candidate = None
                if r_ik is not None and r_kj is not None:
                    candidate = _concat(_concat(r_ik, _star(r_kk)), r_kj)
                new_R[i][j] = _or(r_ij, candidate)
        R = new_R

    # Итог: объединение путей из start во все финальные
    parts: list[str] = []
    for j, st in enumerate(states):
        if st.is_final:
            expr = R[start_idx][j]
            if expr is not None:
                parts.append(expr)

    if not parts:
        return "∅"
    return _or_many(parts)


# ─── Вспомогательные функции для построения РВ-строк ───

def _escape(symbol: str) -> str:
    """
    Экранирует метасимволы через '%'.
    Например: '|' → '%|', '*' → '%*'
    """
    meta = set("|.*+?/[]{}()$%")
    if symbol in meta:
        return f"%{symbol}"
    return symbol


def _star(expr: str | None) -> str:
    """
    Строит замыкание Клини: expr*

    Особые случаи:
    - None или '$' (ε) → '$' (т.к. ε* = ε)
    """
    if expr is None or expr == "$":
        return "$"
    if len(expr) == 1 or (len(expr) == 2 and expr[0] == "%"):
        return f"{expr}*"
    return f"({expr})*"


def _concat(left: str | None, right: str | None) -> str | None:
    """Строит конкатенацию left.right с упрощениями для ε."""
    if left is None or right is None:
        return None
    if left == "$":
        return right
    if right == "$":
        return left
    return f"{left}.{right}"


def _or(left: str | None, right: str | None) -> str | None:
    """Строит дизъюнкцию left|right с простыми упрощениями."""
    if left is None:
        return right
    if right is None:
        return left
    if left == right:
        return left
    return f"{left}|{right}"


def _or_many(parts: list[str]) -> str:
    """Строит дизъюнкцию из списка выражений."""
    if not parts:
        return "∅"
    result: str | None = None
    for p in parts:
        result = _or(result, p)
    return result or "∅"
