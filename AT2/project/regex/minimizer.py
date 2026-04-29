"""Минимизация ДКА алгоритмом Хопкрофта."""

from __future__ import annotations

from regex.dfa import DFA, DFAState


class DFAMinimizer:
    """
    Минимизирует ДКА алгоритмом Хопкрофта.

    Идея:
    - Разбиваем множество состояний на классы эквивалентности.
    - Начальное разбиение: {финальные} и {нефинальные}.
    - Далее поддерживаем очередь (worklist) блоков, которые пытаемся
      использовать для уточнения разбиения.
    - В конце строим новый ДКА, где 1 состояние = 1 класс.

    Важно:
    - В исходном ДКА переходы могут быть частичными (не по каждому символу).
      Для корректной минимизации трактуем отсутствующий переход как переход
      в неявное "поглощающее" (dead) состояние, которое не является финальным
      и имеет петли по всем символам алфавита.
    """

    def minimize(self, dfa: DFA) -> DFA:
        """
        Минимизирует ДКА и возвращает новый минимальный ДКА.

        Реализация следует классическому алгоритму Хопкрофта:
        поддерживаем разбиение P и рабочее множество W.
        """
        if not dfa.states:
            # На практике такого не будет, но защитимся.
            DFAState._counter = 0
            empty_start = DFAState(frozenset())
            empty_start.is_start = True
            return DFA(start=empty_start, states=[empty_start], alphabet=set())

        # 1) Подготовка "полной" функции переходов (с неявным dead-состоянием).
        alphabet = set(dfa.alphabet)
        all_states: set[DFAState] = set(dfa.states)

        needs_dead = any(symbol not in state.transitions for state in all_states for symbol in alphabet)
        dead_state: DFAState | None = None
        if needs_dead and alphabet:
            dead_state = DFAState(frozenset())
            dead_state.is_final = False
            dead_state.is_start = False
            for symbol in alphabet:
                dead_state.add_transition(symbol, dead_state)
            all_states.add(dead_state)

        def delta(state: DFAState, symbol: str) -> DFAState:
            """Полная функция переходов δ(q, a)."""
            if symbol in state.transitions:
                return state.transitions[symbol]
            if dead_state is not None:
                return dead_state
            # Если алфавит пуст или dead не нужен, этот код почти не достижим.
            return state

        # 2) Начальное разбиение P = {F, Q\F}.
        finals = frozenset(s for s in all_states if s.is_final)
        non_finals = frozenset(s for s in all_states if not s.is_final)

        partition: set[frozenset[DFAState]] = set()
        if finals:
            partition.add(finals)
        if non_finals:
            partition.add(non_finals)

        # Рабочий список W: кладем меньший из блоков (классический вариант).
        worklist: set[frozenset[DFAState]] = set()
        if finals and non_finals:
            worklist.add(finals if len(finals) <= len(non_finals) else non_finals)
        elif finals:
            worklist.add(finals)
        elif non_finals:
            worklist.add(non_finals)

        # 3) Для ускорения считаем предобразы переходов:
        # pre[symbol][target_state] = множество source_state таких что δ(source, symbol)=target.
        pre: dict[str, dict[DFAState, set[DFAState]]] = {a: {} for a in alphabet}
        for q in all_states:
            for a in alphabet:
                t = delta(q, a)
                if t not in pre[a]:
                    pre[a][t] = set()
                pre[a][t].add(q)

        # 4) Основной цикл Хопкрофта.
        while worklist:
            a_block = worklist.pop()
            for a in alphabet:
                # X = {q | δ(q,a) ∈ a_block}
                x: set[DFAState] = set()
                for t in a_block:
                    x.update(pre[a].get(t, set()))

                if not x:
                    continue

                new_partition: set[frozenset[DFAState]] = set()
                for y in partition:
                    inter = set(y).intersection(x)
                    diff = set(y).difference(x)
                    if not inter or not diff:
                        new_partition.add(y)
                        continue

                    y1 = frozenset(inter)
                    y2 = frozenset(diff)
                    new_partition.add(y1)
                    new_partition.add(y2)

                    # Обновляем worklist согласно Хопкрофту.
                    if y in worklist:
                        worklist.remove(y)
                        worklist.add(y1)
                        worklist.add(y2)
                    else:
                        worklist.add(y1 if len(y1) <= len(y2) else y2)

                partition = new_partition

        # 5) Строим минимальный ДКА.
        return self._build_minimized_dfa(original_dfa=dfa, partition=partition, delta=delta)

    def _build_minimized_dfa(
        self,
        original_dfa: DFA,
        partition: set[frozenset[DFAState]],
        delta,
    ) -> DFA:
        """
        Строит новый ДКА из разбиения на классы.

        Для каждого блока создаем новое состояние.
        Переходы определяем по представителю блока.
        """
        # Сбрасываем счётчик, чтобы id новых состояний были компактными.
        DFAState._counter = 0

        # Быстрый поиск "состояние -> блок".
        state_to_block: dict[DFAState, frozenset[DFAState]] = {}
        for block in partition:
            for st in block:
                state_to_block[st] = block

        # Создаем новые состояния: по одному на блок.
        block_to_new: dict[frozenset[DFAState], DFAState] = {}
        for block in partition:
            rep = next(iter(block))
            new_state = DFAState(frozenset())
            new_state.is_final = rep.is_final
            block_to_new[block] = new_state

        # Старт.
        start_block = state_to_block[original_dfa.start]
        new_start = block_to_new[start_block]
        new_start.is_start = True

        # Переходы.
        for block in partition:
            rep = next(iter(block))
            new_state = block_to_new[block]
            for symbol in original_dfa.alphabet:
                target = delta(rep, symbol)
                target_block = state_to_block[target]
                new_state.add_transition(symbol, block_to_new[target_block])

        new_states = list(block_to_new.values())
        return DFA(start=new_start, states=new_states, alphabet=set(original_dfa.alphabet))
