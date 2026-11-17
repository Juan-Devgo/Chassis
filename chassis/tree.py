"""Árbol de derivación de Chassis.

Cada nodo interno es un no terminal de R1–R58 junto con la producción que se le
aplicó: sus hijos son, en orden, los símbolos del lado derecho. Una producción
ε deja el nodo sin hijos. Las hojas son los tokens de la entrada.

Las reglas léxicas R59–R67 no se expanden: `<Str>` e `<Id>` aparecen como hojas
con su lexema, en lugar de derivarse carácter a carácter.

La posición (`span`) no participa en la comparación: dos árboles son iguales si
tienen la misma forma y los mismos lexemas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Union

from .source import Span

EPSILON = "ε"


@dataclass(frozen=True)
class Leaf:
    """Terminal de la derivación.

    `symbol` es "Str", "Id" o el propio literal ("mcps", "{", ","...). `text`
    es el lexema; para una cadena, su contenido sin las comillas.
    """

    symbol: str
    text: str
    span: Span = field(compare=False, repr=False)


@dataclass(frozen=True)
class Node:
    """No terminal `symbol` derivado con la regla `rule` (por ejemplo "R5")."""

    symbol: str
    rule: str
    children: tuple[Union["Node", Leaf], ...]
    span: Span = field(compare=False, repr=False)

    def walk(self) -> Iterator[Union["Node", Leaf]]:
        """Recorre el subárbol en preorden, de izquierda a derecha."""
        pila: list[Union[Node, Leaf]] = [self]
        while pila:
            actual = pila.pop()
            yield actual
            if isinstance(actual, Node):
                pila.extend(reversed(actual.children))

    def leaves(self) -> Iterator[Leaf]:
        """Hojas de izquierda a derecha: la cadena derivada."""
        return (n for n in self.walk() if isinstance(n, Leaf))

    def find(self, symbol: str) -> Iterator[Union["Node", Leaf]]:
        """Nodos y hojas del subárbol cuyo símbolo es `symbol`."""
        return (n for n in self.walk() if n.symbol == symbol)


def _etiqueta(nodo: Union[Node, Leaf]) -> str:
    if isinstance(nodo, Node):
        return f"<{nodo.symbol}> ({nodo.rule})"
    if nodo.symbol == "Str":
        return f'<Str> "{nodo.text}"'
    if nodo.symbol == "Id":
        return f"<Id> {nodo.text}"
    return f'"{nodo.text}"'


# Los recorridos usan una pila explícita: una lista de n elementos produce un
# árbol de profundidad 2n y la recursión de Python se agotaría con listas largas.


def format_tree(raiz: Union[Node, Leaf]) -> str:
    """Dibuja el árbol con una línea por nodo; las producciones ε se muestran."""
    lineas = []
    pila = [(raiz, "", "")]  # (nodo, prefijo de su línea, prefijo de sus hijos)
    while pila:
        nodo, propio, descendencia = pila.pop()
        lineas.append(propio + _etiqueta(nodo))
        if not isinstance(nodo, Node):
            continue
        if not nodo.children:
            lineas.append(descendencia + "└── " + EPSILON)
            continue
        ultimo = len(nodo.children) - 1
        for i in range(ultimo, -1, -1):
            if i == ultimo:
                pila.append((nodo.children[i], descendencia + "└── ", descendencia + "    "))
            else:
                pila.append((nodo.children[i], descendencia + "├── ", descendencia + "│   "))
    return "\n".join(lineas)


def to_dict(raiz: Union[Node, Leaf]) -> dict:
    """Convierte el árbol en diccionarios y listas.

    Un nodo queda como {"symbol", "rule", "children"} y una hoja como
    {"symbol", "text"}. Una producción ε tiene "children": [].
    """
    resultado: dict = {}
    pila = [(raiz, resultado)]
    while pila:
        nodo, destino = pila.pop()
        destino["symbol"] = nodo.symbol
        if isinstance(nodo, Node):
            hijos: list[dict] = [{} for _ in nodo.children]
            destino["rule"] = nodo.rule
            destino["children"] = hijos
            pila.extend(zip(nodo.children, hijos))
        else:
            destino["text"] = nodo.text
    return resultado
