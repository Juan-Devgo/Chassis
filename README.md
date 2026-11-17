# chassis-parser

Analizador léxico y sintáctico de **Chassis**, un lenguaje declarativo para
definir el *harness* de un agente de desarrollo asistido por IA: servidores
MCP, skills, agentes y loops.

Está escrito en Python, sin dependencias, como un analizador descendente
recursivo predictivo LL(1) que sigue una a una las reglas R1–R67 del documento
*Reglas y Notación BNF Chassis*. Para una entrada válida construye su árbol de
derivación.

## Requisitos

- Python 3.10 o posterior.
- `pytest` solo para ejecutar las pruebas.

## Uso

```bash
python -m chassis examples/ejemplo.chassis            # comprueba la sintaxis
python -m chassis examples/ejemplo.chassis --tree     # muestra el árbol de derivación
python -m chassis examples/ejemplo.chassis --tokens   # muestra los tokens
```

El código de salida es `0` si el archivo es válido, `1` si tiene un error
léxico o sintáctico y `2` si no se pudo leer.

El análisis se detiene en el primer error e indica la posición, la regla de
producción en la que ocurrió y, cuando es posible, una sugerencia:

```
ejemplos.chassis:134:9: error sintáctico en <Permisos> (R39)
  se esperaba "permissions", se encontró "permission"
            permission: {
            ^~~~~~~~~~
  ¿quisiste decir "permissions"?
```

## Árbol de derivación

`--tree` dibuja el árbol de derivación de la entrada. Cada nodo interno es un
no terminal con la regla que se le aplicó, y sus hijos son, en orden, los
símbolos del lado derecho de esa producción. Las hojas son los tokens, y una
producción vacía se muestra como `ε`:

```
<Chassis> (R1)
├── <SeccionMcps> (R2)
│   ├── "mcps"
│   ├── ":"
│   ├── "{"
│   ├── <ListaProvMcp> (R3)
│   │   ├── <ProvMcp> (R5)
│   │   │   ├── <Str> "provider1"
│   │   │   ├── ":"
│   │   │   ...
│   │   └── <ColaProvMcp> (R4)
│   │       ├── ","
│   │       └── <ListaProvMcp> (R3)
│   │           ...
│   └── "}"
...
```

- Las listas aparecen tal como las define la gramática, recursivas por la
  derecha: `ListaX → X ColaX | ε` y `ColaX → "," ListaX | ε`.
- Las reglas léxicas R59-R67 no se expanden: `<Str>` e `<Id>` son hojas que
  muestran su lexema, en lugar de derivarse carácter a carácter.
- Leídas de izquierda a derecha, las hojas son exactamente los tokens de la
  entrada.

Desde Python:

```python
from chassis import ChassisError, format_tree, parse_file, to_dict

try:
    arbol = parse_file("examples/ejemplo.chassis")
except ChassisError as error:
    print(error.format())
else:
    print(format_tree(arbol))            # el mismo dibujo que --tree
    print(arbol.symbol, arbol.rule)      # Chassis R1
    for agente in arbol.find("AgentLocal"):
        print(agente.children[0].text)   # nombre de cada agente local
    datos = to_dict(arbol)               # diccionarios y listas
```

`Node` tiene `symbol`, `rule`, `children` y `span`; `Leaf` tiene `symbol`,
`text` y `span`. `Node.walk()` recorre el árbol en preorden, `Node.leaves()`
devuelve las hojas y `Node.find(simbolo)` los nodos de un símbolo.

## Estructura

| Archivo | Contenido |
|---|---|
| `chassis/source.py` | Texto fuente y posiciones (línea, columna) |
| `chassis/tokens.py` | Clases de token y palabras reservadas |
| `chassis/lexer.py` | Analizador léxico (R59–R67) |
| `chassis/tree.py` | Árbol de derivación: `Node`, `Leaf`, `format_tree`, `to_dict` |
| `chassis/parser.py` | Analizador sintáctico (R1–R58); un método por no terminal |
| `chassis/errors.py` | `LexError`, `ParseError` y su formato |
| `chassis/cli.py` | Línea de comandos |
| `examples/ejemplo.chassis` | Ejemplo oficial |
| `tests/gramatica.py` | La gramática R1–R58 como tabla, para validar los árboles |
| `tests/` | Pruebas |


> El analizador solo comprueba la sintaxis. No verifica, por ejemplo, que los
agentes citados en un loop estén definidos en `agents`, ni que no haya nombres
repetidos.

## Pruebas

```bash
python -m pip install pytest
python -m pytest
```
