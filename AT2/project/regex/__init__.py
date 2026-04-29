"""Пакет для работы с регулярными выражениями."""

from regex.regex import Regex
from regex.match import Match
from regex.compiled import compile_regex

__all__ = ["Regex", "Match", "compile_regex"]
