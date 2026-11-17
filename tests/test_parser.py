"""Pruebas del analizador sintáctico (R1–R58)."""

import json
from pathlib import Path

import pytest
from gramatica import GRAMATICA

from chassis import LexError, Node, ParseError, format_tree, parse, parse_file, to_dict, tokenize

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLO = RAIZ / "examples" / "ejemplo.chassis"

MINIMO = "mcps:{} skills:{} agents:{} loops:{}"


def doc(mcps="", skills="", agents="", loops=""):
    return f"mcps: {{ {mcps} }}\nskills: {{ {skills} }}\nagents: {{ {agents} }}\nloops: {{ {loops} }}\n"


def cambiar(texto, viejo, nuevo):
    assert texto.count(viejo) == 1, f"{viejo!r} debe aparecer una sola vez"
    return texto.replace(viejo, nuevo)


# Piezas válidas mínimas de cada construcción.
SRV_R = '"s": { label: "l", url: "u" }'
SRV_L = '"s": { label: "l", command: "c", args: ["a"] }'
SK_R = '"k": { command: "c", args: [], url: "u", options: [] }'
SK_L = '"k": { path: "p" }'
ARCHIVO = 'f: { on: "*", read: true, write: false, execute: true }'
PERMISOS = f'permissions: {{ tools: "all", files: [ {ARCHIVO} ] }}'
AG_R = f'"a": {{ command: "c", args: [], url: "u", options: [], model: "m", {PERMISOS}, window-size: "1k" }}'
AG_L = f'"a": {{ path: "p", model: "m", {PERMISOS}, window-size: "1k" }}'
PASO = '"s": { agents: ["a"], context-path: "c" }'
LOOP = f'"l": {{ coordinator-agent: "a", subagents: [], principles-path: "p", steps: [ {PASO} ], dod-path: "d" }}'


def mcp_r(servidores=SRV_R):
    return doc(mcps=f'"p": {{ transport: remote, servers: [ {servidores} ] }}')


def mcp_l(servidores=SRV_L):
    return doc(mcps=f'"p": {{ transport: local, servers: [ {servidores} ] }}')


def skill_r(contextos=SK_R):
    return doc(skills=f'"p": {{ access: remote, contexts: [ {contextos} ] }}')


def skill_l(contextos=SK_L):
    return doc(skills=f'"p": {{ access: local, contexts: [ {contextos} ] }}')


def agent_r(contextos=AG_R):
    return doc(agents=f'"p": {{ access: remote, contexts: [ {contextos} ] }}')


def agent_l(contextos=AG_L):
    return doc(agents=f'"p": {{ access: local, contexts: [ {contextos} ] }}')


# ---------------------------------------------------------------------------
# Entradas válidas
# ---------------------------------------------------------------------------

VALIDOS = {
    "minimo": MINIMO,
    "minimo-sin-espacios": "mcps:{}skills:{}agents:{}loops:{}",
    "minimo-con-saltos-y-tabuladores": "\n\tmcps\t:\n{\n}\n\nskills : { }\nagents:{}\n\tloops:{}\n\n",
    # MCPs
    "mcp-remoto": mcp_r(),
    "mcp-local": mcp_l(),
    "servidores-vacios": mcp_r(""),
    "coma-tras-servers": cambiar(mcp_r(), "] }", "], }"),
    "coma-tras-ultimo-proveedor": cambiar(mcp_r(), "] }", "] },"),
    "dos-proveedores": doc(
        mcps='"a": { transport: remote, servers: [] }, "b": { transport: local, servers: [] }'
    ),
    "dos-servidores-y-coma-final": mcp_r(f"{SRV_R}, {SRV_R},"),
    "coma-tras-url-sin-headers": mcp_r('"s": { label: "l", url: "u", }'),
    "headers-vacio": mcp_r('"s": { label: "l", url: "u", headers: {} }'),
    "headers-con-comas-finales": mcp_r('"s": { label: "l", url: "u", headers: { a: "1", "b c": "2", }, }'),
    "headers-con-reservadas-como-clave": mcp_r(
        '"s": { label: "l", url: "u", headers: { url: "x", true: "y", window-size: "z" } }'
    ),
    "args-vacio": mcp_l('"s": { label: "l", command: "c", args: [] }'),
    "args-con-coma-final": mcp_l('"s": { label: "l", command: "c", args: ["a", "b",] }'),
    "coma-tras-args-sin-env": mcp_l('"s": { label: "l", command: "c", args: [], }'),
    "env-vacio": mcp_l('"s": { label: "l", command: "c", args: [], env: {} }'),
    "dos-servidores-locales": mcp_l(f"{SRV_L}, {SRV_L}"),
    "env-con-coma-final": mcp_l('"s": { label: "l", command: "c", args: [], env: { A_1: "x" }, }'),
    # Skills
    "skill-remota": skill_r(),
    "skill-local": skill_l(),
    "skills-contextos-vacios": skill_r(""),
    "dos-skills-remotas": skill_r(f"{SK_R}, {SK_R}"),
    "skill-remota-coma-final": skill_r('"k": { command: "c", args: [], url: "u", options: ["--x"], }'),
    "skill-local-coma-final": skill_l('"k": { path: "p", },'),
    # Agents
    "agente-remoto": agent_r(),
    "agente-local": agent_l(),
    "agentes-remotos-vacios": agent_r(""),
    "agentes-locales-vacios": agent_l(""),
    "dos-agentes-remotos": agent_r(f"{AG_R}, {AG_R}"),
    "agente-local-coma-final": agent_l(f"{AG_L},"),
    "tools-lista": cambiar(agent_l(), 'tools: "all"', 'tools: ["a", "b"]'),
    "tools-lista-vacia": cambiar(agent_l(), 'tools: "all"', "tools: []"),
    "files-vacio": cambiar(agent_l(), f"[ {ARCHIVO} ]", "[]"),
    "files-dos-reglas-y-coma-final": cambiar(agent_l(), f"[ {ARCHIVO} ]", f"[ {ARCHIVO}, g2_x-y: {{ on: \"d\", read: false, write: false, execute: false, }}, ]"),
    "archivo-con-nombre-reservado": cambiar(agent_l(), "f: {", "read: {"),
    "coma-tras-files": cambiar(agent_l(), "] }, window-size", "], }, window-size"),
    "coma-tras-window-size": cambiar(agent_l(), '"1k" }', '"1k", }'),
    # Loops
    "loop": doc(loops=LOOP),
    "loop-sin-pasos": doc(loops=cambiar(LOOP, f"[ {PASO} ]", "[]")),
    "loop-con-comas-finales": doc(loops=cambiar(LOOP, '"d" }', '"d", },')),
    "paso-con-coma-final": doc(loops=cambiar(LOOP, '"c" }', '"c", },')),
    "todo-junto": doc(
        mcps=f'"a": {{ transport: remote, servers: [ {SRV_R} ] }}, "b": {{ transport: local, servers: [ {SRV_L} ] }}',
        skills=f'"a": {{ access: remote, contexts: [ {SK_R} ] }}, "b": {{ access: local, contexts: [ {SK_L} ] }}',
        agents=f'"a": {{ access: remote, contexts: [ {AG_R} ] }}, "b": {{ access: local, contexts: [ {AG_L} ] }}',
        loops=f"{LOOP}, {LOOP}",
    ),
}


@pytest.mark.parametrize("texto", VALIDOS.values(), ids=VALIDOS.keys())
def test_valido(texto):
    arbol = parse(texto)
    assert isinstance(arbol, Node)
    assert (arbol.symbol, arbol.rule) == ("Chassis", "R1")


# ---------------------------------------------------------------------------
# El árbol es una derivación de la gramática
# ---------------------------------------------------------------------------


def nodos(arbol):
    return [n for n in arbol.walk() if isinstance(n, Node)]


def simbolos(nodo):
    return [hijo.symbol for hijo in nodo.children]


@pytest.mark.parametrize("texto", VALIDOS.values(), ids=VALIDOS.keys())
def test_cada_nodo_aplica_una_produccion(texto):
    arbol = parse(texto)
    for nodo in nodos(arbol):
        regla, alternativas = GRAMATICA[nodo.symbol]
        assert nodo.rule == regla
        assert simbolos(nodo) in alternativas, f"<{nodo.symbol}> en {nodo.span.start}"
    for hoja in arbol.leaves():
        assert hoja.symbol not in GRAMATICA


@pytest.mark.parametrize("texto", VALIDOS.values(), ids=VALIDOS.keys())
def test_las_hojas_son_los_tokens_de_la_entrada(texto):
    hojas = [(h.text, h.span) for h in parse(texto).leaves()]
    tokens = [(t.value, t.span) for t in tokenize(texto)[:-1]]
    assert hojas == tokens


def test_los_casos_validos_ejercitan_todas_las_producciones():
    usadas = {
        (nodo.symbol, tuple(simbolos(nodo)))
        for texto in VALIDOS.values()
        for nodo in nodos(parse(texto))
    }
    todas = {
        (simbolo, tuple(alternativa))
        for simbolo, (_, alternativas) in GRAMATICA.items()
        for alternativa in alternativas
    }
    assert todas - usadas == set()


def test_ejemplo_oficial():
    arbol = parse_file(EJEMPLO)

    def nombres(simbolo):
        return [nodo.children[0].text for nodo in arbol.find(simbolo)]

    assert nombres("ProvMcp") == ["provider1", "provider2"]
    assert nombres("SrvRemoto") == ["supabase-mcp", "context7"]
    assert nombres("SrvLocal") == ["postgres-mcp"]
    assert nombres("ProvSkill") == ["provider1", "provider2"]
    assert nombres("ProvAgent") == ["providerA", "providerB"]
    assert nombres("AgentRemoto") == ["spec-kit-planner"]
    assert nombres("AgentLocal") == ["technician", "little-question-solver"]
    assert nombres("Archivo") == ["all", "docs", "none"]
    assert nombres("Loop") == ["SDD", "bug-fixing"]
    assert nombres("Paso") == ["step1", "step2", "step1", "step2"]
    for nodo in nodos(arbol):
        assert simbolos(nodo) in GRAMATICA[nodo.symbol][1]


def test_ejemplo_oficial_contra_arbol_de_referencia():
    esperado = (RAIZ / "tests" / "esperado" / "ejemplo.arbol.txt").read_text(encoding="utf-8")
    assert format_tree(parse_file(EJEMPLO)) + "\n" == esperado


# ---------------------------------------------------------------------------
# Forma del árbol
# ---------------------------------------------------------------------------


def N(simbolo, regla, *hijos):
    return {"symbol": simbolo, "rule": regla, "children": list(hijos)}


def H(simbolo, texto=None):
    return {"symbol": simbolo, "text": simbolo if texto is None else texto}


def primero(texto, simbolo):
    return next(parse(texto).find(simbolo))


def test_minimo():
    arbol = parse(MINIMO)
    assert simbolos(arbol) == ["SeccionMcps", "SeccionSkills", "SeccionAgents", "SeccionLoops"]
    assert to_dict(arbol.children[0]) == N(
        "SeccionMcps", "R2", H("mcps"), H(":"), H("{"), N("ListaProvMcp", "R3"), H("}")
    )


def test_las_listas_derivan_por_la_derecha():
    # args: ["a", "b",]
    assert to_dict(primero(VALIDOS["args-con-coma-final"], "ListaStr")) == N(
        "ListaStr", "R51",
        H("Str", "a"),
        N("ColaStr", "R52",
          H(","),
          N("ListaStr", "R51",
            H("Str", "b"),
            N("ColaStr", "R52", H(","), N("ListaStr", "R51"))))
    )  # fmt: skip
    # args: ["a"]
    assert to_dict(primero(VALIDOS["mcp-local"], "ListaStr")) == N(
        "ListaStr", "R51", H("Str", "a"), N("ColaStr", "R52")
    )
    # args: []
    assert to_dict(primero(VALIDOS["args-vacio"], "ListaStr")) == N("ListaStr", "R51")


def test_opc_headers_en_sus_tres_formas():
    # url: "u" }
    assert to_dict(primero(VALIDOS["mcp-remoto"], "OpcHeaders")) == N("OpcHeaders", "R10")
    # url: "u", }
    assert to_dict(primero(VALIDOS["coma-tras-url-sin-headers"], "OpcHeaders")) == N(
        "OpcHeaders", "R10", H(","), N("OpcHeadersCuerpo", "R11")
    )
    # url: "u", headers: {} }
    assert to_dict(primero(VALIDOS["headers-vacio"], "OpcHeaders")) == N(
        "OpcHeaders", "R10",
        H(","),
        N("OpcHeadersCuerpo", "R11",
          H("headers"), H(":"), H("{"), N("ListaPares", "R53"), H("}"), N("ComaOpc", "R58"))
    )  # fmt: skip


def test_par_y_clave():
    # headers: { a: "1", "b c": "2", }
    pares = [to_dict(par) for par in parse(VALIDOS["headers-con-comas-finales"]).find("Par")]
    assert pares == [
        N("Par", "R55", N("Clave", "R56", H("Id", "a")), H(":"), H("Str", "1")),
        N("Par", "R55", N("Clave", "R56", H("Str", "b c")), H(":"), H("Str", "2")),
    ]


def test_una_palabra_reservada_puede_ser_identificador():
    claves = [nodo.children[0] for nodo in parse(VALIDOS["headers-con-reservadas-como-clave"]).find("Clave")]
    assert [(hoja.symbol, hoja.text) for hoja in claves] == [("Id", "url"), ("Id", "true"), ("Id", "window-size")]
    archivo = primero(VALIDOS["archivo-con-nombre-reservado"], "Archivo")
    assert simbolos(archivo)[:6] == ["Id", ":", "{", "on", ":", "Str"]
    assert archivo.children[0].text == "read"


def test_alternativas_remote_y_local():
    arbol = parse(VALIDOS["todo-junto"])
    for cuerpo, lista in [("CuerpoMcp", "Srv"), ("CuerpoSkill", "Skill"), ("CuerpoAgent", "Agent")]:
        remoto, local = arbol.find(cuerpo)
        assert remoto.children[0].symbol == "remote"
        assert remoto.children[5].symbol.startswith(f"Lista{lista}Remot")
        assert local.children[0].symbol == "local"
        assert local.children[5].symbol == f"Lista{lista}Local"


def test_herramientas_cadena_o_lista():
    assert to_dict(primero(VALIDOS["agente-local"], "Herramientas")) == N("Herramientas", "R40", H("Str", "all"))
    assert to_dict(primero(VALIDOS["tools-lista-vacia"], "Herramientas")) == N(
        "Herramientas", "R40", H("["), N("ListaStr", "R51"), H("]")
    )


def test_bool():
    valores = [to_dict(nodo) for nodo in parse(VALIDOS["agente-local"]).find("Bool")]
    assert valores == [N("Bool", "R57", H("true")), N("Bool", "R57", H("false")), N("Bool", "R57", H("true"))]


def test_coma_opcional():
    sin_coma = primero(VALIDOS["agente-local"], "AgentLocal")
    con_coma = primero(VALIDOS["coma-tras-window-size"], "AgentLocal")
    assert to_dict(sin_coma.children[-2]) == N("ComaOpc", "R58")
    assert to_dict(con_coma.children[-2]) == N("ComaOpc", "R58", H(","))


def test_la_comparacion_ignora_posiciones():
    assert parse(MINIMO) == parse(VALIDOS["minimo-con-saltos-y-tabuladores"])
    assert parse(mcp_r()) != parse(mcp_l())


def test_posiciones_de_los_nodos():
    arbol = parse('mcps: {\n  "p": { transport: remote, servers: [  ] }\n}\nskills:{} agents:{} loops:{}')
    proveedor = primero_de(arbol, "ProvMcp")
    assert (proveedor.span.start.line, proveedor.span.start.column) == (2, 3)
    assert (proveedor.span.end.line, proveedor.span.end.column) == (2, 44)
    assert (arbol.span.start.line, arbol.span.end.line) == (1, 4)
    # Una producción ε no ocupa texto: se ubica donde termina lo ya leído.
    vacia = primero_de(arbol, "ListaSrvRemoto")
    assert vacia.span.start == vacia.span.end
    assert (vacia.span.start.line, vacia.span.start.column) == (2, 39)


def primero_de(arbol, simbolo):
    return next(arbol.find(simbolo))


def test_format_tree():
    lineas = format_tree(parse(MINIMO)).splitlines()
    assert lineas[:8] == [
        "<Chassis> (R1)",
        "├── <SeccionMcps> (R2)",
        '│   ├── "mcps"',
        '│   ├── ":"',
        '│   ├── "{"',
        "│   ├── <ListaProvMcp> (R3)",
        "│   │   └── ε",
        '│   └── "}"',
    ]
    assert lineas[-7:] == [
        "└── <SeccionLoops> (R44)",
        '    ├── "loops"',
        '    ├── ":"',
        '    ├── "{"',
        "    ├── <ListaLoop> (R45)",
        "    │   └── ε",
        '    └── "}"',
    ]
    assert len(lineas) == 29


def test_format_tree_muestra_los_lexemas():
    texto = format_tree(parse(VALIDOS["agente-local"]))
    assert '├── <Str> "a"\n' in texto
    assert "├── <Id> f\n" in texto
    assert '└── "true"\n' in texto


def test_to_dict_es_serializable():
    datos = to_dict(parse(VALIDOS["todo-junto"]))
    assert json.loads(json.dumps(datos)) == datos
    assert (datos["symbol"], datos["rule"], len(datos["children"])) == ("Chassis", "R1", 4)


def test_las_listas_largas_no_agotan_la_pila():
    # Una lista de n elementos da un árbol de profundidad 2n.
    cantidad = 5000
    elementos = ", ".join(f'"a{i}"' for i in range(cantidad))
    arbol = parse(mcp_l(f'"s": {{ label: "l", command: "c", args: [{elementos}] }}'))
    assert sum(1 for _ in arbol.find("ListaStr")) == cantidad
    assert sum(1 for hoja in arbol.leaves() if hoja.symbol == "Str") == cantidad + 4
    assert to_dict(arbol)["symbol"] == "Chassis"

    corta = ", ".join(f'"a{i}"' for i in range(300))
    dibujo = format_tree(parse(mcp_l(f'"s": {{ label: "l", command: "c", args: [{corta}] }}')))
    assert dibujo.count("<ListaStr> (R51)") == 300


# ---------------------------------------------------------------------------
# Entradas inválidas: (texto, regla donde se detecta, fragmento del mensaje)
# ---------------------------------------------------------------------------

INVALIDOS = {
    # Raíz
    "vacio": ("", "<SeccionMcps> (R2)", 'se esperaba "mcps", se encontró el fin del archivo'),
    "falta-mcps": ("skills:{} agents:{} loops:{}", "<SeccionMcps> (R2)", 'se esperaba "mcps"'),
    "secciones-desordenadas": ("mcps:{} agents:{} skills:{} loops:{}", "<SeccionSkills> (R17)", 'se esperaba "skills"'),
    "falta-loops": ("mcps:{} skills:{} agents:{}", "<SeccionLoops> (R44)", 'se esperaba "loops", se encontró el fin'),
    "coma-entre-secciones": ("mcps:{}, skills:{} agents:{} loops:{}", "<SeccionSkills> (R17)", 'se encontró ","'),
    "seccion-repetida": (MINIMO + " mcps:{}", "<Chassis> (R1)", "se esperaba el fin del archivo"),
    "seccion-sin-dos-puntos": ("mcps {} skills:{} agents:{} loops:{}", "<SeccionMcps> (R2)", 'se esperaba ":"'),
    "seccion-con-corchetes": ("mcps:[] skills:{} agents:{} loops:{}", "<SeccionMcps> (R2)", 'se esperaba "{"'),
    "seccion-entre-comillas": ('"mcps":{} skills:{} agents:{} loops:{}', "<SeccionMcps> (R2)", 'se esperaba "mcps"'),
    "seccion-sin-cerrar": ("mcps:{} skills:{} agents:{} loops:{", "<ListaLoop> (R45)", "se encontró el fin del archivo"),
    # MCPs
    "proveedor-sin-comillas": (cambiar(mcp_r(), '"p":', "p:"), "<ListaProvMcp> (R3)", 'se esperaba una cadena o "}"'),
    "proveedores-sin-coma": (
        doc(mcps='"a": { transport: remote, servers: [] } "b": { transport: local, servers: [] }'),
        "<ColaProvMcp> (R4)",
        'se esperaba "," o "}"',
    ),
    "falta-transport": (doc(mcps='"p": { servers: [] }'), "<ProvMcp> (R5)", 'se esperaba "transport"'),
    "transport-entre-comillas": (cambiar(mcp_r(), "remote", '"remote"'), "<CuerpoMcp> (R6)", 'se esperaba "remote" o "local"'),
    "transport-desconocido": (cambiar(mcp_r(), "remote", "http"), "<CuerpoMcp> (R6)", 'se esperaba "remote" o "local"'),
    "falta-coma-tras-transport": (cambiar(mcp_r(), "remote,", "remote"), "<CuerpoMcp> (R6)", 'se esperaba ","'),
    "contexts-en-vez-de-servers": (cambiar(mcp_r(), "servers", "contexts"), "<CuerpoMcp> (R6)", 'se esperaba "servers"'),
    "servers-con-llaves": (doc(mcps='"p": { transport: remote, servers: {} }'), "<CuerpoMcp> (R6)", 'se esperaba "["'),
    "campo-tras-servers": (cambiar(mcp_r(), "] }", '], label: "x" }'), "<ProvMcp> (R5)", 'se esperaba "}"'),
    "servidores-sin-coma": (mcp_r(f"{SRV_R} {SRV_R}"), "<ColaSrvRemoto> (R8)", 'se esperaba "," o "]"'),
    "servidores-doble-coma": (mcp_r(f"{SRV_R},, {SRV_R}"), "<ListaSrvRemoto> (R7)", 'se esperaba una cadena o "]"'),
    "url-antes-de-label": (mcp_r('"s": { url: "u", label: "l" }'), "<SrvRemoto> (R9)", 'se esperaba "label"'),
    "falta-url": (mcp_r('"s": { label: "l" }'), "<SrvRemoto> (R9)", 'se esperaba ","'),
    "falta-coma-entre-campos": (mcp_r('"s": { label: "l" url: "u" }'), "<SrvRemoto> (R9)", 'se esperaba ","'),
    "falta-dos-puntos": (mcp_r('"s": { label "l", url: "u" }'), "<SrvRemoto> (R9)", 'se esperaba ":"'),
    "valor-sin-comillas": (mcp_r('"s": { label: l, url: "u" }'), "<SrvRemoto> (R9)", "se esperaba una cadena"),
    "campo-desconocido-tras-url": (mcp_r('"s": { label: "l", url: "u", timeout: "5" }'), "<OpcHeadersCuerpo> (R11)", 'se esperaba "headers" o "}"'),
    "url-seguida-de-cadena": (mcp_r('"s": { label: "l", url: "u" "v" }'), "<OpcHeaders> (R10)", 'se esperaba "," o "}"'),
    "headers-con-corchetes": (mcp_r('"s": { label: "l", url: "u", headers: [] }'), "<OpcHeadersCuerpo> (R11)", 'se esperaba "{"'),
    "campo-tras-headers": (mcp_r('"s": { label: "l", url: "u", headers: {}, env: {} }'), "<SrvRemoto> (R9)", 'se esperaba "}"'),
    "par-con-valor-sin-comillas": (mcp_r('"s": { label: "l", url: "u", headers: { a: b } }'), "<Par> (R55)", "se esperaba una cadena"),
    "par-sin-dos-puntos": (mcp_r('"s": { label: "l", url: "u", headers: { a "b" } }'), "<Par> (R55)", 'se esperaba ":"'),
    "pares-doble-coma": (mcp_r('"s": { label: "l", url: "u", headers: { a: "1",, b: "2" } }'), "<ListaPares> (R53)", 'se esperaba un identificador, una cadena o "}"'),
    "pares-sin-coma": (mcp_r('"s": { label: "l", url: "u", headers: { a: "1" b: "2" } }'), "<ColaPares> (R54)", 'se esperaba "," o "}"'),
    "servidor-remoto-en-proveedor-local": (mcp_l(SRV_R), "<SrvLocal> (R14)", 'se esperaba "command"'),
    "servidor-local-en-proveedor-remoto": (mcp_r(SRV_L), "<SrvRemoto> (R9)", 'se esperaba "url"'),
    "falta-args": (mcp_l('"s": { label: "l", command: "c" }'), "<SrvLocal> (R14)", 'se esperaba ","'),
    "args-como-cadena": (mcp_l('"s": { label: "l", command: "c", args: "a" }'), "<SrvLocal> (R14)", 'se esperaba "["'),
    "args-doble-coma": (mcp_l('"s": { label: "l", command: "c", args: ["a",, "b"] }'), "<ListaStr> (R51)", 'se esperaba una cadena o "]"'),
    "args-coma-inicial": (mcp_l('"s": { label: "l", command: "c", args: [,] }'), "<ListaStr> (R51)", 'se esperaba una cadena o "]"'),
    "args-sin-coma": (mcp_l('"s": { label: "l", command: "c", args: ["a" "b"] }'), "<ColaStr> (R52)", 'se esperaba "," o "]"'),
    "args-sin-comillas": (mcp_l('"s": { label: "l", command: "c", args: [a] }'), "<ListaStr> (R51)", 'se esperaba una cadena o "]"'),
    "args-sin-cerrar": (mcp_l('"s": { label: "l", command: "c", args: ["a" }'), "<ColaStr> (R52)", 'se esperaba "," o "]"'),
    "campo-desconocido-tras-args": (mcp_l('"s": { label: "l", command: "c", args: [], cwd: "x" }'), "<OpcEnvCuerpo> (R16)", 'se esperaba "env" o "}"'),
    "args-seguido-de-cadena": (mcp_l('"s": { label: "l", command: "c", args: [] "x" }'), "<OpcEnv> (R15)", 'se esperaba "," o "}"'),
    "env-con-corchetes": (mcp_l('"s": { label: "l", command: "c", args: [], env: [] }'), "<OpcEnvCuerpo> (R16)", 'se esperaba "{"'),
    "campo-tras-env": (mcp_l('"s": { label: "l", command: "c", args: [], env: {}, url: "u" }'), "<SrvLocal> (R14)", 'se esperaba "}"'),
    # Skills
    "falta-access": (doc(skills='"p": { contexts: [] }'), "<ProvSkill> (R20)", 'se esperaba "access"'),
    "access-desconocido": (cambiar(skill_r(), "remote", "git"), "<CuerpoSkill> (R21)", 'se esperaba "remote" o "local"'),
    "servers-en-vez-de-contexts": (cambiar(skill_r(), "contexts", "servers"), "<CuerpoSkill> (R21)", 'se esperaba "contexts"'),
    "skills-sin-coma": (skill_l(f"{SK_L} {SK_L}"), "<ColaSkillLocal> (R26)", 'se esperaba "," o "]"'),
    "skill-local-en-proveedor-remoto": (skill_r(SK_L), "<SkillRemota> (R24)", 'se esperaba "command"'),
    "skill-remota-en-proveedor-local": (skill_l(SK_R), "<SkillLocal> (R27)", 'se esperaba "path"'),
    "skill-remota-sin-options": (skill_r('"k": { command: "c", args: [], url: "u" }'), "<SkillRemota> (R24)", 'se esperaba ","'),
    "skill-remota-url-antes-de-args": (skill_r('"k": { command: "c", url: "u", args: [], options: [] }'), "<SkillRemota> (R24)", 'se esperaba "args"'),
    "skill-remota-campo-extra": (skill_r('"k": { command: "c", args: [], url: "u", options: [], model: "m" }'), "<SkillRemota> (R24)", 'se esperaba "}"'),
    "skill-local-campo-extra": (skill_l('"k": { path: "p", url: "u" }'), "<SkillLocal> (R27)", 'se esperaba "}"'),
    "skill-local-path-seguido-de-cadena": (skill_l('"k": { path: "p" "q" }'), "<SkillLocal> (R27)", 'se esperaba "," o "}"'),
    "skill-local-vacia": (skill_l('"k": {}'), "<SkillLocal> (R27)", 'se esperaba "path"'),
    # Agents
    "agentes-sin-coma": (agent_l(f"{AG_L} {AG_L}"), "<ColaAgentLocal> (R37)", 'se esperaba "," o "]"'),
    "agente-local-en-proveedor-remoto": (agent_r(AG_L), "<AgentRemoto> (R35)", 'se esperaba "command"'),
    "agente-remoto-en-proveedor-local": (agent_l(AG_R), "<AgentLocal> (R38)", 'se esperaba "path"'),
    "agente-remoto-sin-model": (cambiar(agent_r(), 'model: "m", ', ""), "<AgentRemoto> (R35)", 'se esperaba "model"'),
    "agente-local-sin-model": (cambiar(agent_l(), 'model: "m", ', ""), "<AgentLocal> (R38)", 'se esperaba "model"'),
    "agente-sin-permisos": (cambiar(agent_l(), f"{PERMISOS}, ", ""), "<Permisos> (R39)", 'se esperaba "permissions"'),
    "agente-sin-window-size": (cambiar(agent_l(), ', window-size: "1k"', ""), "<AgentLocal> (R38)", 'se esperaba ","'),
    "window-size-sin-comillas": (cambiar(agent_l(), '"1k"', "grande"), "<AgentLocal> (R38)", "se esperaba una cadena"),
    "agente-campo-extra": (cambiar(agent_l(), '"1k" }', '"1k", url: "u" }'), "<AgentLocal> (R38)", 'se esperaba "}"'),
    "permission-en-singular": (cambiar(agent_l(), "permissions", "permission"), "<Permisos> (R39)", 'se esperaba "permissions", se encontró "permission"'),
    "permisos-sin-tools": (cambiar(agent_l(), 'tools: "all", ', ""), "<Permisos> (R39)", 'se esperaba "tools"'),
    "permisos-sin-files": (cambiar(agent_l(), f", files: [ {ARCHIVO} ]", ""), "<Permisos> (R39)", 'se esperaba ","'),
    "permisos-files-antes-de-tools": (cambiar(agent_l(), f'tools: "all", files: [ {ARCHIVO} ]', 'files: [], tools: "all"'), "<Permisos> (R39)", 'se esperaba "tools"'),
    "files-con-llaves": (cambiar(agent_l(), f"[ {ARCHIVO} ]", "{}"), "<Permisos> (R39)", 'se esperaba "["'),
    "tools-booleano": (cambiar(agent_l(), '"all"', "true"), "<Herramientas> (R40)", 'se esperaba una cadena o "["'),
    "tools-objeto": (cambiar(agent_l(), '"all"', "{}"), "<Herramientas> (R40)", 'se esperaba una cadena o "["'),
    "archivo-con-nombre-entre-comillas": (cambiar(agent_l(), "f: {", '"f": {'), "<ListaArchivos> (R41)", 'se esperaba un identificador o "]"'),
    "archivos-sin-coma": (cambiar(agent_l(), f"[ {ARCHIVO} ]", f"[ {ARCHIVO} {ARCHIVO} ]"), "<ColaArchivos> (R42)", 'se esperaba "," o "]"'),
    "archivo-sin-on": (cambiar(agent_l(), 'on: "*", ', ""), "<Archivo> (R43)", 'se esperaba "on"'),
    "archivo-write-antes-de-read": (cambiar(agent_l(), "read: true, write: false", "write: false, read: true"), "<Archivo> (R43)", 'se esperaba "read"'),
    "archivo-sin-execute": (cambiar(agent_l(), ", execute: true", ""), "<Archivo> (R43)", 'se esperaba ","'),
    "archivo-campo-extra": (cambiar(agent_l(), "execute: true", "execute: true, delete: true"), "<Archivo> (R43)", 'se esperaba "}"'),
    "bool-desconocido": (cambiar(agent_l(), "read: true", "read: yes"), "<Bool> (R57)", 'se esperaba "true" o "false"'),
    "bool-entre-comillas": (cambiar(agent_l(), "read: true", 'read: "true"'), "<Bool> (R57)", 'se esperaba "true" o "false"'),
    "bool-en-mayusculas": (cambiar(agent_l(), "read: true", "read: True"), "<Bool> (R57)", 'se esperaba "true" o "false"'),
    # Loops
    "loops-sin-coma": (doc(loops=f"{LOOP} {LOOP}"), "<ColaLoop> (R46)", 'se esperaba "," o "}"'),
    "loop-sin-coordinador": (doc(loops=cambiar(LOOP, 'coordinator-agent: "a", ', "")), "<Loop> (R47)", 'se esperaba "coordinator-agent"'),
    "loop-coordinador-lista": (doc(loops=cambiar(LOOP, 'coordinator-agent: "a"', 'coordinator-agent: ["a"]')), "<Loop> (R47)", "se esperaba una cadena"),
    "loop-subagents-cadena": (doc(loops=cambiar(LOOP, "subagents: []", 'subagents: "a"')), "<Loop> (R47)", 'se esperaba "["'),
    "loop-sin-principles-path": (doc(loops=cambiar(LOOP, 'principles-path: "p", ', "")), "<Loop> (R47)", 'se esperaba "principles-path"'),
    "loop-sin-steps": (doc(loops=cambiar(LOOP, f"steps: [ {PASO} ], ", "")), "<Loop> (R47)", 'se esperaba "steps"'),
    "loop-sin-dod-path": (doc(loops=cambiar(LOOP, ', dod-path: "d"', "")), "<Loop> (R47)", 'se esperaba ","'),
    "loop-campo-extra": (doc(loops=cambiar(LOOP, '"d" }', '"d", model: "m" }')), "<Loop> (R47)", 'se esperaba "}"'),
    "pasos-sin-coma": (doc(loops=cambiar(LOOP, f"[ {PASO} ]", f"[ {PASO} {PASO} ]")), "<ColaPaso> (R49)", 'se esperaba "," o "]"'),
    "paso-sin-agents": (doc(loops=cambiar(LOOP, 'agents: ["a"], ', "")), "<Paso> (R50)", 'se esperaba "agents"'),
    "paso-agents-cadena": (doc(loops=cambiar(LOOP, 'agents: ["a"]', 'agents: "a"')), "<Paso> (R50)", 'se esperaba "["'),
    "paso-sin-context-path": (doc(loops=cambiar(LOOP, ', context-path: "c"', "")), "<Paso> (R50)", 'se esperaba ","'),
    "paso-campo-extra": (doc(loops=cambiar(LOOP, '"c" }', '"c", path: "p" }')), "<Paso> (R50)", 'se esperaba "}"'),
}


@pytest.mark.parametrize("texto, regla, fragmento", INVALIDOS.values(), ids=INVALIDOS.keys())
def test_invalido(texto, regla, fragmento):
    with pytest.raises(ParseError) as error:
        parse(texto)
    assert error.value.rule == regla
    assert fragmento in error.value.message


def test_un_error_lexico_se_informa_antes_que_el_sintactico():
    with pytest.raises(LexError):
        parse('agents:{} mcps:{ "año": {} }')


# ---------------------------------------------------------------------------
# Ubicación y sugerencias
# ---------------------------------------------------------------------------


def error_de(texto, nombre="<entrada>"):
    with pytest.raises(ParseError) as error:
        parse(texto, nombre)
    return error.value


def test_ejemplo_original_falla_en_la_linea_134():
    # El ejemplo entregado decía `permission:` en el tercer agente; R39 exige
    # `permissions`. El archivo de examples/ ya tiene la corrección.
    texto = EJEMPLO.read_text(encoding="utf-8")
    antes, separador, despues = texto.rpartition("permissions:")
    assert separador
    error = error_de(antes + "permission:" + despues, "ejemplos.chassis")
    assert (error.line, error.column) == (134, 9)
    assert error.format().splitlines() == [
        "ejemplos.chassis:134:9: error sintáctico en <Permisos> (R39)",
        '  se esperaba "permissions", se encontró "permission"',
        "            permission: {",
        "            ^~~~~~~~~~",
        '  ¿quisiste decir "permissions"?',
    ]


def test_el_senalador_respeta_los_tabuladores():
    error = error_de('mcps: {\n\t\t"p": { transport: http }\n}')
    assert (error.line, error.column) == (2, 21)
    assert error.format().splitlines()[2:4] == [
        '    \t\t"p": { transport: http }',
        "    \t\t" + " " * 18 + "^~~~",
    ]


@pytest.mark.parametrize(
    "caso, sugerencia",
    [
        ("permission-en-singular", '¿quisiste decir "permissions"?'),
        ("contexts-en-vez-de-servers", 'el orden es fijo: aquí corresponde "servers"'),
        ("secciones-desordenadas", 'el orden es fijo: aquí corresponde "skills"'),
        ("url-antes-de-label", 'el orden es fijo: aquí corresponde "label"'),
        ("transport-entre-comillas", "las palabras reservadas se escriben sin comillas: remote"),
        ("seccion-entre-comillas", "las palabras reservadas se escriben sin comillas: mcps"),
        ("bool-entre-comillas", "las palabras reservadas se escriben sin comillas: true"),
        ("proveedor-sin-comillas", 'las cadenas se escriben entre comillas dobles: "p"'),
        ("valor-sin-comillas", 'las cadenas se escriben entre comillas dobles: "l"'),
        ("args-sin-comillas", 'las cadenas se escriben entre comillas dobles: "a"'),
        ("archivo-con-nombre-entre-comillas", "los identificadores se escriben sin comillas: f"),
        ("bool-en-mayusculas", '¿quisiste decir "true"?'),
        ("bool-desconocido", None),
        ("falta-url", None),
    ],
)
def test_sugerencias(caso, sugerencia):
    texto, _, _ = INVALIDOS[caso]
    assert error_de(texto).hint == sugerencia
