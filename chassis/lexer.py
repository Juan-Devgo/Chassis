"""Analizador léxico de Chassis (R59–R67)."""

from __future__ import annotations

import string

from .errors import LexError
from .source import Position, Source, Span
from .tokens import Token, TokenKind

LETTERS = frozenset(string.ascii_letters)  # <Letra> (R65)
DIGITS = frozenset(string.digits)  # <Digito> (R66)
IDENT_REST = LETTERS | DIGITS | frozenset("_-")  # <IdResto> (R64)
WHITESPACE = frozenset(" \t\n")  # <Esp> (R67)

#: <SimStr> (R62) del documento de reglas.
STR_SYMBOLS_BASE = frozenset("{}[]':-_@/=,.* ")
#: Ampliación de R62 acordada para admitir URL con consulta, fragmento y
#: codificación porcentual, y rutas con barra invertida.
STR_SYMBOLS_EXTRA = frozenset("?&#%+\\")
#: <Car> (R61). No hay secuencias de escape: "\" es un carácter más.
STR_ALPHABET = LETTERS | DIGITS | STR_SYMBOLS_BASE | STR_SYMBOLS_EXTRA

PUNCTUATION = {
    "{": TokenKind.LBRACE,
    "}": TokenKind.RBRACE,
    "[": TokenKind.LBRACKET,
    "]": TokenKind.RBRACKET,
    ":": TokenKind.COLON,
    ",": TokenKind.COMMA,
}

_AYUDA_ALFABETO = (
    "se admiten letras sin tilde, dígitos, el espacio y los símbolos "
    "{ } [ ] ' : - _ @ / = , . * ? & # % + \\"
)


def _describir(caracter: str) -> str:
    if caracter == "\t":
        return "un tabulador"
    if caracter == "\r":
        return "un retorno de carro"
    if caracter.isprintable():
        return f'"{caracter}"'
    return f"U+{ord(caracter):04X}"


class Lexer:
    """Convierte el texto fuente en tokens. Se detiene en el primer error."""

    def __init__(self, source: Source) -> None:
        self._source = source
        self._text = source.text
        self._offset = 0
        self._line = 1
        self._column = 1

    def tokens(self) -> list[Token]:
        """Devuelve todos los tokens; el último es siempre EOF."""
        resultado = []
        while True:
            token = self._siguiente()
            resultado.append(token)
            if token.kind is TokenKind.EOF:
                return resultado

    # -- cursor ------------------------------------------------------------

    def _pos(self) -> Position:
        return Position(self._offset, self._line, self._column)

    def _actual(self) -> str:
        """Carácter bajo el cursor, o "" al final del texto."""
        if self._offset < len(self._text):
            return self._text[self._offset]
        return ""

    def _avanzar(self) -> None:
        if self._text[self._offset] == "\n":
            self._line += 1
            self._column = 1
        else:
            self._column += 1
        self._offset += 1

    def _error(
        self, mensaje: str, inicio: Position, *, rule: str | None = None, hint: str | None = None
    ) -> LexError:
        return LexError(mensaje, Span(inicio, self._pos()), self._source, rule=rule, hint=hint)

    # -- tokens ------------------------------------------------------------

    def _siguiente(self) -> Token:
        while self._actual() in WHITESPACE:  # <Esp> (R67)
            self._avanzar()

        inicio = self._pos()
        caracter = self._actual()
        if caracter == "":
            return Token(TokenKind.EOF, "", Span(inicio, inicio))
        if caracter in PUNCTUATION:
            self._avanzar()
            return Token(PUNCTUATION[caracter], caracter, Span(inicio, self._pos()))
        if caracter == '"':
            return self._cadena(inicio)
        if caracter in LETTERS:
            return self._palabra(inicio)
        raise self._inesperado(inicio)

    def _cadena(self, inicio: Position) -> Token:
        """<Str> ::= '"' <Texto> '"' (R59–R62)."""
        self._avanzar()  # comilla de apertura
        comienzo = self._offset
        while True:
            caracter = self._actual()
            if caracter == "" or caracter == "\n":
                raise self._error(
                    "cadena sin cerrar",
                    inicio,
                    rule="<Str> (R59)",
                    hint="las cadenas ocupan una sola línea y terminan con comillas dobles",
                )
            if caracter == '"':
                valor = self._text[comienzo : self._offset]
                self._avanzar()  # comilla de cierre
                return Token(TokenKind.STR, valor, Span(inicio, self._pos()))
            if caracter not in STR_ALPHABET:
                aqui = self._pos()
                self._avanzar()
                raise self._error(
                    f"carácter no permitido dentro de una cadena: {_describir(caracter)}",
                    aqui,
                    rule="<Car> (R61–R62)",
                    hint=_AYUDA_ALFABETO,
                )
            self._avanzar()

    def _palabra(self, inicio: Position) -> Token:
        """<Id> ::= <Letra> <IdResto> (R63–R64), con coincidencia más larga."""
        comienzo = self._offset
        while self._actual() in IDENT_REST:
            self._avanzar()
        return Token(TokenKind.WORD, self._text[comienzo : self._offset], Span(inicio, self._pos()))

    def _inesperado(self, inicio: Position) -> LexError:
        caracter = self._actual()

        if caracter in IDENT_REST:  # dígito, "_" o "-": no puede iniciar un <Id>
            comienzo = self._offset
            while self._actual() in IDENT_REST:
                self._avanzar()
            lexema = self._text[comienzo : self._offset]
            return self._error(
                f'"{lexema}" no es un token válido: un identificador debe empezar por una letra',
                inicio,
                rule="<Id> (R63)",
                hint="si es un valor, escríbelo entre comillas dobles",
            )

        hint = None
        if caracter == "'":
            hint = "las cadenas se escriben con comillas dobles"
        elif caracter == "#" or self._text.startswith(("//", "/*"), self._offset):
            hint = "Chassis no admite comentarios"
        elif caracter == "\r":
            hint = "los saltos de línea deben ser LF"
        self._avanzar()
        return self._error(
            f"carácter inesperado: {_describir(caracter)}",
            inicio,
            hint=hint,
        )
