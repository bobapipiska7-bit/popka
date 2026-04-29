"""Модуль результата поиска и симуляции НКА с группами захвата."""

from __future__ import annotations


class Match:
    """
    Результат успешного поиска.

    Содержит информацию о найденном вхождении и группах захвата.
    """

    def __init__(self, string: str, start: int, end: int, groups: list[str | None]):
        """
        Создаёт объект Match.

        Параметры:
            string: исходная строка поиска
            start: позиция начала совпадения (включительно)
            end: позиция конца совпадения (не включительно)
            groups: список групп захвата (группа 1, группа 2, ...)
        """
        self._string = string
        self._start = start
        self._end = end
        self._groups = groups

    @property
    def start(self) -> int:
        """Начальная позиция вхождения."""
        return self._start

    @property
    def end(self) -> int:
        """Конечная позиция вхождения (не включительно)."""
        return self._end

    @property
    def string(self) -> str:
        """Найденная подстрока."""
        return self._string[self._start : self._end]

    @property
    def source(self) -> str:
        """Исходная строка."""
        return self._string

    def group(self, index: int = 0) -> str | None:
        """
        Возвращает группу захвата по индексу.

        group(0) — всё совпадение
        group(1) — первая группа захвата
        group(2) — вторая группа захвата
        ...
        """
        if index == 0:
            return self.string
        if index <= len(self._groups):
            return self._groups[index - 1]
        raise IndexError(f"Группа {index} не существует")

    def __getitem__(self, index: int) -> str | None:
        """Оператор индексации: match[0], match[1], ..."""
        return self.group(index)

    def __iter__(self):
        """Итератор по группам захвата (начиная с группы 0)."""
        yield self.string
        yield from self._groups

    def __bool__(self) -> bool:
        """Match всегда True если существует."""
        return True

    def __repr__(self) -> str:
        """Отладочное строковое представление."""
        return (
            f"Match(string='{self.string}', "
            f"start={self._start}, "
            f"end={self._end}, "
            f"groups={self._groups})"
        )


class GroupTracker:
    """
    Отслеживает группы захвата во время симуляции НКА.

    Хранит для каждой группы: начальную и конечную позицию.
    """

    def __init__(self) -> None:
        """Создаёт пустой трекер групп захвата."""
        self.groups: dict[int, tuple[int | None, int | None]] = {}

    def start_group(self, group_num: int, pos: int) -> None:
        """Фиксируем начало группы."""
        self.groups[group_num] = (pos, None)

    def end_group(self, group_num: int, pos: int) -> None:
        """Фиксируем конец группы."""
        if group_num in self.groups:
            start, _ = self.groups[group_num]
            self.groups[group_num] = (start, pos)

    def get_group_strings(self, string: str) -> list[str | None]:
        """
        Возвращает список строк групп захвата.

        Порядок: группа 1, группа 2, ...
        """
        if not self.groups:
            return []

        max_group = max(self.groups.keys())
        result: list[str | None] = []
        for i in range(1, max_group + 1):
            if i not in self.groups:
                result.append(None)
                continue

            start, end = self.groups[i]
            if start is not None and end is not None:
                result.append(string[start:end])
            else:
                result.append(None)
        return result

    def copy(self) -> "GroupTracker":
        """Создаёт копию трекера (для ветвления НКА)."""
        new_tracker = GroupTracker()
        new_tracker.groups = dict(self.groups)
        return new_tracker


def simulate_nfa_with_groups(nfa, string: str, start_pos: int) -> Match | None:
    """
    Симулирует НКА на подстроке string начиная с позиции start_pos.

    Отслеживает группы захвата.
    Возвращает Match если найдено совпадение, иначе None.

    Возвращает САМОЕ ДЛИННОЕ совпадение, начинающееся в start_pos.
    """
    from regex.nfa import EPSILON

    # Конфигурация симуляции: (текущее состояние, трекер групп)
    Thread = tuple[object, GroupTracker]

    def _apply_group_markers(state, trk: GroupTracker, pos: int) -> None:
        """Применяет маркеры начала/конца групп, если они есть в состоянии."""
        group_starts = getattr(state, "group_starts", None)
        if group_starts:
            for g in group_starts:
                trk.start_group(g, pos)
        else:
            if getattr(state, "group_start", None) is not None:
                trk.start_group(state.group_start, pos)

        group_ends = getattr(state, "group_ends", None)
        if group_ends:
            for g in group_ends:
                trk.end_group(g, pos)
        else:
            if getattr(state, "group_end", None) is not None:
                trk.end_group(state.group_end, pos)

    def _epsilon_closure_threads(threads: list[Thread], pos: int) -> list[Thread]:
        """
        Epsilon-замыкание для набора нитей.

        Важно: при epsilon-ветвлениях копируем трекер, чтобы сохранить
        корректные границы групп по разным путям.
        """
        stack: list[Thread] = list(threads)
        result: list[Thread] = []
        seen: set[tuple[int, tuple[tuple[int, tuple[int | None, int | None]], ...]]] = set()

        while stack:
            state, trk = stack.pop()
            _apply_group_markers(state, trk, pos)

            signature = (state.id, tuple(sorted(trk.groups.items())))
            if signature in seen:
                continue
            seen.add(signature)
            result.append((state, trk))

            for next_state in getattr(state, "transitions", {}).get(EPSILON, []):
                stack.append((next_state, trk.copy()))

        return result

    # Инициализация.
    initial_tracker = GroupTracker()
    current: list[Thread] = _epsilon_closure_threads([(nfa.start, initial_tracker)], start_pos)

    best_match: Match | None = None
    pos = start_pos

    def _update_best(threads: list[Thread], end_pos: int) -> None:
        """
        Если есть финальные состояния — обновляем лучшее (самое длинное) совпадение.

        На одной и той же позиции может быть несколько финальных "нитей"
        (разные пути НКА). Для групп захвата важно выбрать нить, в которой
        корректно проставлено больше групп (меньше None).
        """
        nonlocal best_match
        best_groups: list[str | None] | None = None
        best_score: int = -1

        for st, trk in threads:
            if not getattr(st, "is_final", False):
                continue

            groups = trk.get_group_strings(string)
            score = sum(1 for g in groups if g is not None)
            if score > best_score:
                best_score = score
                best_groups = groups

        if best_groups is not None:
            best_match = Match(string, start_pos, end_pos, best_groups)

    # Пустое совпадение на старте.
    _update_best(current, pos)

    # Читаем символы, сохраняя самое длинное совпадение.
    while pos < len(string) and current:
        char = string[pos]
        next_threads: list[Thread] = []

        for state, trk in current:
            for next_state in getattr(state, "transitions", {}).get(char, []):
                next_threads.append((next_state, trk.copy()))

        pos += 1
        current = _epsilon_closure_threads(next_threads, pos)
        _update_best(current, pos)

    return best_match
