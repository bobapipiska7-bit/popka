from regex import Regex


def demo_search() -> None:
    print("=== SEARCH ===")
    r = Regex("(a|b)+c")
    print(r.search("xxabc"))  # (2, 5)
    match = r.search("xxabc", groups=True)
    print(match[0])  # "abc"
    print(match[1])  # последняя группа


def demo_compile() -> None:
    print("=== COMPILE ===")
    r = Regex("[a-z]+").compile()
    print(r._get_compiled().dfa.accepts("hello"))  # True
    print(r._get_compiled().dfa.accepts("Hello"))  # False


def demo_complement() -> None:
    print("=== ДОПОЛНЕНИЕ ===")
    r = Regex("hello").compile()
    comp = r.complement()
    # Важно: search() ищет подстроку, а не проверяет принадлежность строки языку.
    # Поэтому для complement/difference корректнее демонстрировать accepts().
    # Ещё нюанс: complement строится над Σ* для Σ = алфавит ДКА.
    # Для "hello" это Σ={h,e,l,o}, поэтому проверяем строки над этим Σ.
    print(comp._get_compiled().dfa.accepts("hell"))   # True
    print(comp._get_compiled().dfa.accepts("hello"))  # False
    print(comp._get_compiled().dfa.accepts(""))       # True


def demo_difference() -> None:
    print("=== РАЗНОСТЬ ===")
    r1 = Regex("[a-z]+").compile()
    r2 = Regex("hello").compile()
    diff = r1.difference(r2)
    print(diff._get_compiled().dfa.accepts("world"))  # True
    print(diff._get_compiled().dfa.accepts("hello"))  # False


def demo_restore() -> None:
    print("=== ВОССТАНОВЛЕНИЕ РВ ===")
    r = Regex("(a|b)*c").compile()
    print(r.restore())  # восстановленное РВ


if __name__ == "__main__":
    demo_search()
    demo_compile()
    demo_complement()
    demo_difference()
    demo_restore()
