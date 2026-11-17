"""Errores léxicos y sintácticos, y su presentación."""

from __future__ import annotations

from .source import Source, Span


class ChassisError(Exception):
    """Error localizado en el texto fuente.

    `rule` nombra la regla de producción en la que se detectó, por ejemplo
    "<Permisos> (R39)". `hint` es una sugerencia opcional para corregirlo.
    """

    kind = "error"

    def __init__(
        self,
        message: str,
        span: Span,
        source: Source,
        *,
        rule: str | None = None,
        hint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.span = span
        self.source = source
        self.rule = rule
        self.hint = hint

    @property
    def line(self) -> int:
        return self.span.start.line

    @property
    def column(self) -> int:
        return self.span.start.column

    def format(self) -> str:
        """Mensaje completo: ubicación, regla, fragmento señalado y sugerencia."""
        start = self.span.start
        cabecera = f"{self.source.name}:{start.line}:{start.column}: {self.kind}"
        if self.rule:
            cabecera += f" en {self.rule}"
        lineas = [cabecera, f"  {self.message}"]

        texto = self.source.line_text(start.line)
        if texto.strip():
            # Se conservan los tabuladores para que el señalador quede alineado
            # sin importar el ancho de tabulación de la terminal.
            sangria = "".join(c if c == "\t" else " " for c in texto[: start.column - 1])
            if self.span.end.line == start.line:
                ancho = self.span.end.column - start.column
            else:
                ancho = len(texto) - (start.column - 1)
            ancho = max(1, ancho)
            lineas.append(f"    {texto.rstrip()}")
            lineas.append(f"    {sangria}^{'~' * (ancho - 1)}")

        if self.hint:
            lineas.append(f"  {self.hint}")
        return "\n".join(lineas)

    def __str__(self) -> str:
        return self.format()


class LexError(ChassisError):
    kind = "error léxico"


class ParseError(ChassisError):
    kind = "error sintáctico"
