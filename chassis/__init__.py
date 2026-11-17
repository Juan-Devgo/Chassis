"""Analizador léxico y sintáctico del lenguaje declarativo Chassis."""

from __future__ import annotations

from .errors import ChassisError, LexError, ParseError
from .lexer import Lexer
from .source import Position, Source, Span
from .tokens import KEYWORDS, Token, TokenKind

__all__ = [
    "KEYWORDS",
    "ChassisError",
    "LexError",
    "Lexer",
    "ParseError",
    "Position",
    "Source",
    "Span",
    "Token",
    "TokenKind",
    "tokenize",
]


def tokenize(text: str, name: str = "<entrada>") -> list[Token]:
    """Devuelve los tokens de `text`. Lanza LexError si hay un error léxico."""
    return Lexer(Source(text, name)).tokens()
