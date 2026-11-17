"""Analizador léxico y sintáctico del lenguaje declarativo Chassis."""

from __future__ import annotations

from .errors import ChassisError, LexError, ParseError
from .lexer import Lexer
from .parser import Parser
from .source import Position, Source, Span
from .tokens import KEYWORDS, Token, TokenKind
from .tree import Leaf, Node, format_tree, to_dict

__all__ = [
    "KEYWORDS",
    "ChassisError",
    "Leaf",
    "LexError",
    "Lexer",
    "Node",
    "ParseError",
    "Parser",
    "Position",
    "Source",
    "Span",
    "Token",
    "TokenKind",
    "format_tree",
    "parse",
    "parse_file",
    "parse_source",
    "to_dict",
    "tokenize",
]


def tokenize(text: str, name: str = "<entrada>") -> list[Token]:
    """Devuelve los tokens de `text`. Lanza LexError si hay un error léxico."""
    return Lexer(Source(text, name)).tokens()


def parse_source(source: Source) -> Node:
    return Parser(Lexer(source).tokens(), source).parse()


def parse(text: str, name: str = "<entrada>") -> Node:
    """Analiza `text` y devuelve su árbol de derivación.

    Lanza LexError o ParseError si la entrada no pertenece al lenguaje.
    """
    return parse_source(Source(text, name))


def parse_file(path) -> Node:
    """Analiza el archivo `path` y devuelve su árbol de derivación."""
    return parse_source(Source.from_file(path))
