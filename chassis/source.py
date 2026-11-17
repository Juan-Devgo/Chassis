"""Texto fuente y posiciones dentro de él."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    """Un punto del texto fuente. `line` y `column` empiezan en 1."""

    offset: int
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.line}:{self.column}"


@dataclass(frozen=True)
class Span:
    """Tramo del texto fuente. `end` apunta justo después del último carácter."""

    start: Position
    end: Position


class Source:
    """Texto a analizar junto con el nombre que se muestra en los errores."""

    def __init__(self, text: str, name: str = "<entrada>") -> None:
        self.text = text
        self.name = name
        self._lines = text.split("\n")

    @classmethod
    def from_file(cls, path) -> "Source":
        # El modo texto convierte CRLF en "\n", así que <Esp> (R67) no necesita
        # "\r". "utf-8-sig" descarta la marca BOM si el editor la añadió.
        with open(path, encoding="utf-8-sig") as archivo:
            return cls(archivo.read(), str(path))

    def line_text(self, line: int) -> str:
        """Devuelve la línea `line` (desde 1) sin el salto de línea."""
        if 1 <= line <= len(self._lines):
            return self._lines[line - 1]
        return ""
