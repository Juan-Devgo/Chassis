"""Línea de comandos: `python -m chassis archivo [--tokens] [--tree]`."""

from __future__ import annotations

import argparse
import sys

from .errors import ChassisError
from .lexer import Lexer
from .parser import Parser
from .source import Source
from .tree import format_tree

SALIDA_VALIDO = 0
SALIDA_ERROR = 1  # error léxico o sintáctico
SALIDA_USO = 2  # no se pudo leer el archivo o argumentos incorrectos


def main(argv: list[str] | None = None) -> int:
    opciones = argparse.ArgumentParser(
        prog="chassis",
        description="Comprueba la sintaxis de un archivo Chassis.",
    )
    opciones.add_argument("archivo", help="archivo Chassis que se va a analizar")
    opciones.add_argument("--tokens", action="store_true", help="muestra los tokens")
    opciones.add_argument("--tree", action="store_true", help="muestra el árbol de derivación")
    args = opciones.parse_args(argv)

    try:
        source = Source.from_file(args.archivo)
    except OSError as error:
        print(f"chassis: no se pudo leer {args.archivo}: {error.strerror}", file=sys.stderr)
        return SALIDA_USO
    except UnicodeDecodeError:
        print(f"chassis: {args.archivo} no es un archivo de texto UTF-8", file=sys.stderr)
        return SALIDA_USO

    try:
        tokens = Lexer(source).tokens()
        if args.tokens:
            for token in tokens:
                print(f"{token.span.start}\t{token.kind.name}\t{token.value}")
        arbol = Parser(tokens, source).parse()
    except ChassisError as error:
        print(error.format(), file=sys.stderr)
        return SALIDA_ERROR

    if args.tree:
        print(format_tree(arbol))
    elif not args.tokens:
        print(f"{source.name}: sintaxis válida")
    return SALIDA_VALIDO
