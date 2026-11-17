"""Tokens del lenguaje Chassis."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .source import Span


class TokenKind(Enum):
    STR = "cadena"  # <Str> (R59)
    WORD = "palabra"  # palabra reservada o <Id> (R63)
    LBRACE = "{"
    RBRACE = "}"
    LBRACKET = "["
    RBRACKET = "]"
    COLON = ":"
    COMMA = ","
    EOF = "fin del archivo"


#: Terminales alfabéticos de R1–R58. Comparten forma léxica con <Id>, por lo
#: que son reservadas contextuales: el analizador sintáctico decide según la
#: regla en curso si una palabra actúa como reservada o como identificador.
KEYWORDS = frozenset(
    {
        # MCPs
        "mcps", "transport", "remote", "local", "servers", "label", "url",
        "headers", "command", "args", "env",
        # Skills
        "skills", "access", "contexts", "options", "path",
        # Agents
        "agents", "model", "permissions", "tools", "files", "on", "read",
        "write", "execute", "window-size",
        # Loops
        "loops", "coordinator-agent", "subagents", "principles-path", "steps",
        "dod-path", "context-path",
        # Bool
        "true", "false",
    }
)


@dataclass(frozen=True)
class Token:
    """Unidad léxica.

    `value` es el contenido sin comillas para STR, el lexema para WORD y los
    signos de puntuación, y la cadena vacía para EOF.
    """

    kind: TokenKind
    value: str
    span: Span

    @property
    def is_keyword(self) -> bool:
        return self.kind is TokenKind.WORD and self.value in KEYWORDS

    def describe(self) -> str:
        """Texto con el que el token aparece en los mensajes de error."""
        if self.kind is TokenKind.STR:
            return f'la cadena "{self.value}"'
        if self.kind is TokenKind.EOF:
            return "el fin del archivo"
        return f'"{self.value}"'
