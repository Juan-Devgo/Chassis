"""Analizador sintáctico de Chassis (R1–R58).

Descendente recursivo y predictivo: la gramática es LL(1), así que cada
decisión se toma mirando un solo token y nunca se retrocede. Cada no terminal
tiene su método, que devuelve los hijos de su nodo en el orden de la producción
aplicada; el resultado es el árbol de derivación de la entrada.
"""

from __future__ import annotations

import difflib
import functools
from typing import Callable

from .errors import ParseError
from .source import Position, Source, Span
from .tokens import KEYWORDS, Token, TokenKind
from .tree import Leaf, Node

STR = TokenKind.STR
WORD = TokenKind.WORD
LBRACE = TokenKind.LBRACE
RBRACE = TokenKind.RBRACE
LBRACKET = TokenKind.LBRACKET
RBRACKET = TokenKind.RBRACKET
COLON = TokenKind.COLON
COMMA = TokenKind.COMMA
EOF = TokenKind.EOF

#: Marca "aquí se esperaba un <Id>". Los demás elementos esperados son una
#: clase de token (TokenKind) o el texto de una palabra reservada (str).
ID = object()


def regla(nombre: str, numero: str, *, contexto: bool = True):
    """Convierte un método en la regla `nombre`.

    El método devuelve la lista de hijos de la producción aplicada (vacía para
    ε) y el decorador la envuelve en un nodo. Con `contexto`, los errores que
    ocurran dentro se atribuyen a esta regla.
    """

    def decorador(metodo):
        @functools.wraps(metodo)
        def envoltura(self, *args, **kwargs):
            if contexto:
                self._reglas.append((nombre, numero))
            try:
                hijos = metodo(self, *args, **kwargs)
            finally:
                if contexto:
                    self._reglas.pop()
            return self._nodo(nombre, numero, hijos)

        return envoltura

    return decorador


def _es_cadena(token: Token) -> bool:
    return token.kind is STR


def _es_palabra(token: Token) -> bool:
    return token.kind is WORD


def _es_clave(token: Token) -> bool:
    return token.kind is WORD or token.kind is STR


def _describir(esperado) -> str:
    if esperado is ID:
        return "un identificador"
    if esperado is STR:
        return "una cadena"
    if esperado is EOF:
        return "el fin del archivo"
    if isinstance(esperado, TokenKind):
        return f'"{esperado.value}"'
    return f'"{esperado}"'


def _unir(textos: list[str]) -> str:
    if len(textos) == 1:
        return textos[0]
    return ", ".join(textos[:-1]) + " o " + textos[-1]


class Parser:
    """Construye el árbol de derivación. Se detiene en el primer error."""

    def __init__(self, tokens: list[Token], source: Source) -> None:
        self._tokens = tokens
        self._source = source
        self._i = 0
        self._reglas: list[tuple[str, str]] = []

    def parse(self) -> Node:
        raiz = self._chassis()
        if self._ver().kind is not EOF:
            self._reglas.append(("Chassis", "R1"))
            raise self._error([EOF])
        return raiz

    # -- primitivas --------------------------------------------------------

    def _ver(self) -> Token:
        return self._tokens[self._i]

    def _avanzar(self) -> Token:
        token = self._tokens[self._i]
        if token.kind is not EOF:
            self._i += 1
        return token

    def _viene(self, palabra: str) -> bool:
        token = self._ver()
        return token.kind is WORD and token.value == palabra

    def _fin_previo(self) -> Position:
        """Dónde termina lo ya consumido: ahí se ubican las producciones ε."""
        if self._i == 0:
            return self._tokens[0].span.start
        return self._tokens[self._i - 1].span.end

    def _nodo(self, nombre: str, numero: str, hijos: list) -> Node:
        if hijos:
            span = Span(hijos[0].span.start, hijos[-1].span.end)
        else:
            span = Span(self._fin_previo(), self._fin_previo())
        return Node(nombre, numero, tuple(hijos), span)

    # Cada primitiva consume un terminal y devuelve su hoja.

    def _t(self, clase: TokenKind) -> Leaf:
        """Signo de puntuación."""
        if self._ver().kind is not clase:
            raise self._error([clase])
        token = self._avanzar()
        return Leaf(token.value, token.value, token.span)

    def _kw(self, palabra: str) -> Leaf:
        """Palabra reservada."""
        if not self._viene(palabra):
            raise self._error([palabra])
        token = self._avanzar()
        return Leaf(palabra, token.value, token.span)

    def _str(self) -> Leaf:
        """<Str> (R59)."""
        if self._ver().kind is not STR:
            raise self._error([STR])
        token = self._avanzar()
        return Leaf("Str", token.value, token.span)

    def _id(self) -> Leaf:
        """<Id> (R63)."""
        # Cualquier palabra sirve como <Id>, también las reservadas (p. ej.
        # una cabecera llamada `url`): el contexto ya dice que aquí va un <Id>.
        if self._ver().kind is not WORD:
            raise self._error([ID])
        token = self._avanzar()
        return Leaf("Id", token.value, token.span)

    def _campo(self, palabra: str) -> list[Leaf]:
        """Nombre de campo y dos puntos: `"label" ":"`."""
        return [self._kw(palabra), self._t(COLON)]

    # -- errores -----------------------------------------------------------

    def _error(self, esperados: list) -> ParseError:
        token = self._ver()
        nombre, numero = self._reglas[-1]
        mensaje = (
            f"se esperaba {_unir([_describir(e) for e in esperados])}, "
            f"se encontró {token.describe()}"
        )
        return ParseError(
            mensaje,
            token.span,
            self._source,
            rule=f"<{nombre}> ({numero})",
            hint=self._sugerencia(esperados, token),
        )

    @staticmethod
    def _sugerencia(esperados: list, token: Token) -> str | None:
        reservadas = [e for e in esperados if isinstance(e, str)]
        if token.kind is WORD:
            if reservadas and token.value not in KEYWORDS:
                parecidas = difflib.get_close_matches(token.value, reservadas, n=1, cutoff=0.6)
                if parecidas:
                    return f'¿quisiste decir "{parecidas[0]}"?'
            elif len(reservadas) == 1:
                return f'el orden es fijo: aquí corresponde "{reservadas[0]}"'
            if STR in esperados and ID not in esperados:
                return f'las cadenas se escriben entre comillas dobles: "{token.value}"'
        elif token.kind is STR:
            if token.value in reservadas:
                return f"las palabras reservadas se escriben sin comillas: {token.value}"
            if ID in esperados and STR not in esperados:
                return f"los identificadores se escriben sin comillas: {token.value}"
        return None

    # -- piezas compartidas ------------------------------------------------

    def _lista(
        self,
        lista: tuple[str, str],
        cola: tuple[str, str],
        elemento: Callable[[], Node],
        empieza: Callable[[Token], bool],
        esperado: list,
        cierre: TokenKind,
    ) -> Node:
        """Par de reglas `ListaX → X ColaX | ε` y `ColaX → "," ListaX | ε`.

        `lista` y `cola` son (nombre, número) de cada regla. No consume el
        cierre: eso lo hace la regla que contiene la lista.

        La derivación es recursiva por la derecha, pero aquí se leen los
        elementos con un bucle y los nodos anidados se arman al final, para que
        la profundidad de la pila no dependa del tamaño de la lista.
        """
        piezas: list[tuple[Node, Leaf | None]] = []  # (elemento, coma que lo sigue)
        while empieza(self._ver()):
            nodo = elemento()
            coma = self._t(COMMA) if self._ver().kind is COMMA else None
            piezas.append((nodo, coma))
            if coma is None:
                break

        # Tras un elemento sin coma se está en ColaX; al inicio o tras una
        # coma, en ListaX. En ambos casos ε exige FOLLOW = { cierre }.
        if self._ver().kind is not cierre:
            if piezas and piezas[-1][1] is None:
                self._reglas.append(cola)
                raise self._error([COMMA, cierre])
            self._reglas.append(lista)
            raise self._error([*esperado, cierre])

        resto = self._nodo(*lista, [])  # ListaX → ε
        for nodo, coma in reversed(piezas):
            if coma is None:
                siguiente = self._nodo(*cola, [])  # ColaX → ε
            else:
                siguiente = self._nodo(*cola, [coma, resto])  # ColaX → "," ListaX
            resto = self._nodo(*lista, [nodo, siguiente])  # ListaX → X ColaX
        return resto

    def _seccion(self, palabra: str, lista: Callable[[], Node]) -> list:
        """Forma común de R2, R17, R28 y R44: `palabra ":" "{" ListaX "}"`."""
        return [*self._campo(palabra), self._t(LBRACE), lista(), self._t(RBRACE)]

    def _proveedor(self, campo: str, cuerpo: Callable[[], Node]) -> list:
        """Forma común de R5, R20 y R31: `<Str> ":" "{" campo ":" CuerpoX "}"`."""
        return [
            self._str(),
            self._t(COLON),
            self._t(LBRACE),
            *self._campo(campo),
            cuerpo(),
            self._t(RBRACE),
        ]

    def _cuerpo(self, campo: str, remota: Callable[[], Node], local: Callable[[], Node]) -> list:
        """Forma común de R6, R21 y R32:
        `"remote" "," campo ":" "[" ListaRemota "]" <ComaOpc>`
        `| "local" "," campo ":" "[" ListaLocal "]" <ComaOpc>`"""
        if self._viene("remote"):
            modo, lista = "remote", remota
        elif self._viene("local"):
            modo, lista = "local", local
        else:
            raise self._error(["remote", "local"])
        return [
            self._kw(modo),
            self._t(COMMA),
            *self._campo(campo),
            self._t(LBRACKET),
            lista(),
            self._t(RBRACKET),
            self._coma_opc(),
        ]

    def _arreglo_str(self) -> list:
        """`"[" <ListaStr> "]"`, la única forma en que aparece <ListaStr>."""
        return [self._t(LBRACKET), self._lista_str(), self._t(RBRACKET)]

    def _bloque_remoto(self) -> list:
        """Campos `command, args, url, options` comunes a R24 y R35."""
        return [
            *self._campo("command"),
            self._str(),
            self._t(COMMA),
            *self._campo("args"),
            *self._arreglo_str(),
            self._t(COMMA),
            *self._campo("url"),
            self._str(),
            self._t(COMMA),
            *self._campo("options"),
            *self._arreglo_str(),
        ]

    def _cola_agente(self) -> list:
        """Final común de R35 y R38:
        `"," "model" ":" <Str> "," <Permisos> "," "window-size" ":" <Str> <ComaOpc> "}"`"""
        return [
            self._t(COMMA),
            *self._campo("model"),
            self._str(),
            self._t(COMMA),
            self._permisos(),
            self._t(COMMA),
            *self._campo("window-size"),
            self._str(),
            self._coma_opc(),
            self._t(RBRACE),
        ]

    # -- raíz --------------------------------------------------------------

    @regla("Chassis", "R1")
    def _chassis(self):
        """<Chassis> ::= <SeccionMcps> <SeccionSkills> <SeccionAgents> <SeccionLoops>"""
        return [
            self._seccion_mcps(),
            self._seccion_skills(),
            self._seccion_agents(),
            self._seccion_loops(),
        ]

    # -- MCPs --------------------------------------------------------------

    @regla("SeccionMcps", "R2")
    def _seccion_mcps(self):
        """<SeccionMcps> ::= "mcps" ":" "{" <ListaProvMcp> "}" """
        return self._seccion("mcps", self._lista_prov_mcp)

    def _lista_prov_mcp(self) -> Node:
        """<ListaProvMcp> ::= <ProvMcp> <ColaProvMcp> | ε
        <ColaProvMcp> ::= "," <ListaProvMcp> | ε"""
        return self._lista(
            ("ListaProvMcp", "R3"), ("ColaProvMcp", "R4"), self._prov_mcp, _es_cadena, [STR], RBRACE
        )

    @regla("ProvMcp", "R5")
    def _prov_mcp(self):
        """<ProvMcp> ::= <Str> ":" "{" "transport" ":" <CuerpoMcp> "}" """
        return self._proveedor("transport", self._cuerpo_mcp)

    @regla("CuerpoMcp", "R6")
    def _cuerpo_mcp(self):
        """<CuerpoMcp> ::= "remote" "," "servers" ":" "[" <ListaSrvRemoto> "]" <ComaOpc>
        | "local" "," "servers" ":" "[" <ListaSrvLocal> "]" <ComaOpc>"""
        return self._cuerpo("servers", self._lista_srv_remoto, self._lista_srv_local)

    def _lista_srv_remoto(self) -> Node:
        """<ListaSrvRemoto> ::= <SrvRemoto> <ColaSrvRemoto> | ε
        <ColaSrvRemoto> ::= "," <ListaSrvRemoto> | ε"""
        return self._lista(
            ("ListaSrvRemoto", "R7"), ("ColaSrvRemoto", "R8"), self._srv_remoto, _es_cadena, [STR], RBRACKET
        )

    @regla("SrvRemoto", "R9")
    def _srv_remoto(self):
        """<SrvRemoto> ::= <Str> ":" "{" "label" ":" <Str> "," "url" ":" <Str> <OpcHeaders> "}" """
        return [
            self._str(),
            self._t(COLON),
            self._t(LBRACE),
            *self._campo("label"),
            self._str(),
            self._t(COMMA),
            *self._campo("url"),
            self._str(),
            self._opc_headers(),
            self._t(RBRACE),
        ]

    @regla("OpcHeaders", "R10")
    def _opc_headers(self):
        """<OpcHeaders> ::= "," <OpcHeadersCuerpo> | ε"""
        if self._ver().kind is COMMA:
            return [self._t(COMMA), self._opc_headers_cuerpo()]
        if self._ver().kind is RBRACE:  # FOLLOW(OpcHeaders)
            return []
        raise self._error([COMMA, RBRACE])

    @regla("OpcHeadersCuerpo", "R11")
    def _opc_headers_cuerpo(self):
        """<OpcHeadersCuerpo> ::= "headers" ":" "{" <ListaPares> "}" <ComaOpc> | ε"""
        if self._viene("headers"):
            return [
                *self._campo("headers"),
                self._t(LBRACE),
                self._lista_pares(),
                self._t(RBRACE),
                self._coma_opc(),
            ]
        if self._ver().kind is RBRACE:  # FOLLOW(OpcHeadersCuerpo)
            return []
        raise self._error(["headers", RBRACE])

    def _lista_srv_local(self) -> Node:
        """<ListaSrvLocal> ::= <SrvLocal> <ColaSrvLocal> | ε
        <ColaSrvLocal> ::= "," <ListaSrvLocal> | ε"""
        return self._lista(
            ("ListaSrvLocal", "R12"), ("ColaSrvLocal", "R13"), self._srv_local, _es_cadena, [STR], RBRACKET
        )

    @regla("SrvLocal", "R14")
    def _srv_local(self):
        """<SrvLocal> ::= <Str> ":" "{" "label" ":" <Str> "," "command" ":" <Str> ","
        "args" ":" "[" <ListaStr> "]" <OpcEnv> "}" """
        return [
            self._str(),
            self._t(COLON),
            self._t(LBRACE),
            *self._campo("label"),
            self._str(),
            self._t(COMMA),
            *self._campo("command"),
            self._str(),
            self._t(COMMA),
            *self._campo("args"),
            *self._arreglo_str(),
            self._opc_env(),
            self._t(RBRACE),
        ]

    @regla("OpcEnv", "R15")
    def _opc_env(self):
        """<OpcEnv> ::= "," <OpcEnvCuerpo> | ε"""
        if self._ver().kind is COMMA:
            return [self._t(COMMA), self._opc_env_cuerpo()]
        if self._ver().kind is RBRACE:  # FOLLOW(OpcEnv)
            return []
        raise self._error([COMMA, RBRACE])

    @regla("OpcEnvCuerpo", "R16")
    def _opc_env_cuerpo(self):
        """<OpcEnvCuerpo> ::= "env" ":" "{" <ListaPares> "}" <ComaOpc> | ε"""
        if self._viene("env"):
            return [
                *self._campo("env"),
                self._t(LBRACE),
                self._lista_pares(),
                self._t(RBRACE),
                self._coma_opc(),
            ]
        if self._ver().kind is RBRACE:  # FOLLOW(OpcEnvCuerpo)
            return []
        raise self._error(["env", RBRACE])

    # -- Skills ------------------------------------------------------------

    @regla("SeccionSkills", "R17")
    def _seccion_skills(self):
        """<SeccionSkills> ::= "skills" ":" "{" <ListaProvSkill> "}" """
        return self._seccion("skills", self._lista_prov_skill)

    def _lista_prov_skill(self) -> Node:
        """<ListaProvSkill> ::= <ProvSkill> <ColaProvSkill> | ε
        <ColaProvSkill> ::= "," <ListaProvSkill> | ε"""
        return self._lista(
            ("ListaProvSkill", "R18"), ("ColaProvSkill", "R19"), self._prov_skill, _es_cadena, [STR], RBRACE
        )

    @regla("ProvSkill", "R20")
    def _prov_skill(self):
        """<ProvSkill> ::= <Str> ":" "{" "access" ":" <CuerpoSkill> "}" """
        return self._proveedor("access", self._cuerpo_skill)

    @regla("CuerpoSkill", "R21")
    def _cuerpo_skill(self):
        """<CuerpoSkill> ::= "remote" "," "contexts" ":" "[" <ListaSkillRemota> "]" <ComaOpc>
        | "local" "," "contexts" ":" "[" <ListaSkillLocal> "]" <ComaOpc>"""
        return self._cuerpo("contexts", self._lista_skill_remota, self._lista_skill_local)

    def _lista_skill_remota(self) -> Node:
        """<ListaSkillRemota> ::= <SkillRemota> <ColaSkillRemota> | ε
        <ColaSkillRemota> ::= "," <ListaSkillRemota> | ε"""
        return self._lista(
            ("ListaSkillRemota", "R22"), ("ColaSkillRemota", "R23"), self._skill_remota, _es_cadena, [STR], RBRACKET
        )

    @regla("SkillRemota", "R24")
    def _skill_remota(self):
        """<SkillRemota> ::= <Str> ":" "{" "command" ":" <Str> "," "args" ":" "[" <ListaStr> "]" ","
        "url" ":" <Str> "," "options" ":" "[" <ListaStr> "]" <ComaOpc> "}" """
        return [
            self._str(),
            self._t(COLON),
            self._t(LBRACE),
            *self._bloque_remoto(),
            self._coma_opc(),
            self._t(RBRACE),
        ]

    def _lista_skill_local(self) -> Node:
        """<ListaSkillLocal> ::= <SkillLocal> <ColaSkillLocal> | ε
        <ColaSkillLocal> ::= "," <ListaSkillLocal> | ε"""
        return self._lista(
            ("ListaSkillLocal", "R25"), ("ColaSkillLocal", "R26"), self._skill_local, _es_cadena, [STR], RBRACKET
        )

    @regla("SkillLocal", "R27")
    def _skill_local(self):
        """<SkillLocal> ::= <Str> ":" "{" "path" ":" <Str> <ComaOpc> "}" """
        return [
            self._str(),
            self._t(COLON),
            self._t(LBRACE),
            *self._campo("path"),
            self._str(),
            self._coma_opc(),
            self._t(RBRACE),
        ]

    # -- Agents ------------------------------------------------------------

    @regla("SeccionAgents", "R28")
    def _seccion_agents(self):
        """<SeccionAgents> ::= "agents" ":" "{" <ListaProvAgent> "}" """
        return self._seccion("agents", self._lista_prov_agent)

    def _lista_prov_agent(self) -> Node:
        """<ListaProvAgent> ::= <ProvAgent> <ColaProvAgent> | ε
        <ColaProvAgent> ::= "," <ListaProvAgent> | ε"""
        return self._lista(
            ("ListaProvAgent", "R29"), ("ColaProvAgent", "R30"), self._prov_agent, _es_cadena, [STR], RBRACE
        )

    @regla("ProvAgent", "R31")
    def _prov_agent(self):
        """<ProvAgent> ::= <Str> ":" "{" "access" ":" <CuerpoAgent> "}" """
        return self._proveedor("access", self._cuerpo_agent)

    @regla("CuerpoAgent", "R32")
    def _cuerpo_agent(self):
        """<CuerpoAgent> ::= "remote" "," "contexts" ":" "[" <ListaAgentRemoto> "]" <ComaOpc>
        | "local" "," "contexts" ":" "[" <ListaAgentLocal> "]" <ComaOpc>"""
        return self._cuerpo("contexts", self._lista_agent_remoto, self._lista_agent_local)

    def _lista_agent_remoto(self) -> Node:
        """<ListaAgentRemoto> ::= <AgentRemoto> <ColaAgentRemoto> | ε
        <ColaAgentRemoto> ::= "," <ListaAgentRemoto> | ε"""
        return self._lista(
            ("ListaAgentRemoto", "R33"), ("ColaAgentRemoto", "R34"), self._agent_remoto, _es_cadena, [STR], RBRACKET
        )

    @regla("AgentRemoto", "R35")
    def _agent_remoto(self):
        """<AgentRemoto> ::= <Str> ":" "{" "command" ":" <Str> "," "args" ":" "[" <ListaStr> "]" ","
        "url" ":" <Str> "," "options" ":" "[" <ListaStr> "]" "," "model" ":" <Str> ","
        <Permisos> "," "window-size" ":" <Str> <ComaOpc> "}" """
        return [
            self._str(),
            self._t(COLON),
            self._t(LBRACE),
            *self._bloque_remoto(),
            *self._cola_agente(),
        ]

    def _lista_agent_local(self) -> Node:
        """<ListaAgentLocal> ::= <AgentLocal> <ColaAgentLocal> | ε
        <ColaAgentLocal> ::= "," <ListaAgentLocal> | ε"""
        return self._lista(
            ("ListaAgentLocal", "R36"), ("ColaAgentLocal", "R37"), self._agent_local, _es_cadena, [STR], RBRACKET
        )

    @regla("AgentLocal", "R38")
    def _agent_local(self):
        """<AgentLocal> ::= <Str> ":" "{" "path" ":" <Str> "," "model" ":" <Str> ","
        <Permisos> "," "window-size" ":" <Str> <ComaOpc> "}" """
        return [
            self._str(),
            self._t(COLON),
            self._t(LBRACE),
            *self._campo("path"),
            self._str(),
            *self._cola_agente(),
        ]

    @regla("Permisos", "R39")
    def _permisos(self):
        """<Permisos> ::= "permissions" ":" "{" "tools" ":" <Herramientas> ","
        "files" ":" "[" <ListaArchivos> "]" <ComaOpc> "}" """
        return [
            *self._campo("permissions"),
            self._t(LBRACE),
            *self._campo("tools"),
            self._herramientas(),
            self._t(COMMA),
            *self._campo("files"),
            self._t(LBRACKET),
            self._lista_archivos(),
            self._t(RBRACKET),
            self._coma_opc(),
            self._t(RBRACE),
        ]

    @regla("Herramientas", "R40")
    def _herramientas(self):
        """<Herramientas> ::= <Str> | "[" <ListaStr> "]" """
        if self._ver().kind is STR:
            return [self._str()]
        if self._ver().kind is LBRACKET:
            return self._arreglo_str()
        raise self._error([STR, LBRACKET])

    def _lista_archivos(self) -> Node:
        """<ListaArchivos> ::= <Archivo> <ColaArchivos> | ε
        <ColaArchivos> ::= "," <ListaArchivos> | ε"""
        return self._lista(
            ("ListaArchivos", "R41"), ("ColaArchivos", "R42"), self._archivo, _es_palabra, [ID], RBRACKET
        )

    @regla("Archivo", "R43")
    def _archivo(self):
        """<Archivo> ::= <Id> ":" "{" "on" ":" <Str> "," "read" ":" <Bool> ","
        "write" ":" <Bool> "," "execute" ":" <Bool> <ComaOpc> "}" """
        return [
            self._id(),
            self._t(COLON),
            self._t(LBRACE),
            *self._campo("on"),
            self._str(),
            self._t(COMMA),
            *self._campo("read"),
            self._bool(),
            self._t(COMMA),
            *self._campo("write"),
            self._bool(),
            self._t(COMMA),
            *self._campo("execute"),
            self._bool(),
            self._coma_opc(),
            self._t(RBRACE),
        ]

    # -- Loops -------------------------------------------------------------

    @regla("SeccionLoops", "R44")
    def _seccion_loops(self):
        """<SeccionLoops> ::= "loops" ":" "{" <ListaLoop> "}" """
        return self._seccion("loops", self._lista_loop)

    def _lista_loop(self) -> Node:
        """<ListaLoop> ::= <Loop> <ColaLoop> | ε
        <ColaLoop> ::= "," <ListaLoop> | ε"""
        return self._lista(("ListaLoop", "R45"), ("ColaLoop", "R46"), self._loop, _es_cadena, [STR], RBRACE)

    @regla("Loop", "R47")
    def _loop(self):
        """<Loop> ::= <Str> ":" "{" "coordinator-agent" ":" <Str> ","
        "subagents" ":" "[" <ListaStr> "]" "," "principles-path" ":" <Str> ","
        "steps" ":" "[" <ListaPaso> "]" "," "dod-path" ":" <Str> <ComaOpc> "}" """
        return [
            self._str(),
            self._t(COLON),
            self._t(LBRACE),
            *self._campo("coordinator-agent"),
            self._str(),
            self._t(COMMA),
            *self._campo("subagents"),
            *self._arreglo_str(),
            self._t(COMMA),
            *self._campo("principles-path"),
            self._str(),
            self._t(COMMA),
            *self._campo("steps"),
            self._t(LBRACKET),
            self._lista_paso(),
            self._t(RBRACKET),
            self._t(COMMA),
            *self._campo("dod-path"),
            self._str(),
            self._coma_opc(),
            self._t(RBRACE),
        ]

    def _lista_paso(self) -> Node:
        """<ListaPaso> ::= <Paso> <ColaPaso> | ε
        <ColaPaso> ::= "," <ListaPaso> | ε"""
        return self._lista(("ListaPaso", "R48"), ("ColaPaso", "R49"), self._paso, _es_cadena, [STR], RBRACKET)

    @regla("Paso", "R50")
    def _paso(self):
        """<Paso> ::= <Str> ":" "{" "agents" ":" "[" <ListaStr> "]" ","
        "context-path" ":" <Str> <ComaOpc> "}" """
        return [
            self._str(),
            self._t(COLON),
            self._t(LBRACE),
            *self._campo("agents"),
            *self._arreglo_str(),
            self._t(COMMA),
            *self._campo("context-path"),
            self._str(),
            self._coma_opc(),
            self._t(RBRACE),
        ]

    # -- comunes -----------------------------------------------------------

    def _lista_str(self) -> Node:
        """<ListaStr> ::= <Str> <ColaStr> | ε
        <ColaStr> ::= "," <ListaStr> | ε"""
        return self._lista(("ListaStr", "R51"), ("ColaStr", "R52"), self._str, _es_cadena, [STR], RBRACKET)

    def _lista_pares(self) -> Node:
        """<ListaPares> ::= <Par> <ColaPares> | ε
        <ColaPares> ::= "," <ListaPares> | ε"""
        return self._lista(("ListaPares", "R53"), ("ColaPares", "R54"), self._par, _es_clave, [ID, STR], RBRACE)

    @regla("Par", "R55")
    def _par(self):
        """<Par> ::= <Clave> ":" <Str>"""
        return [self._clave(), self._t(COLON), self._str()]

    @regla("Clave", "R56")
    def _clave(self):
        """<Clave> ::= <Id> | <Str>"""
        if self._ver().kind is STR:
            return [self._str()]
        if self._ver().kind is WORD:
            return [self._id()]
        raise self._error([ID, STR])

    @regla("Bool", "R57")
    def _bool(self):
        """<Bool> ::= "true" | "false" """
        if self._viene("true"):
            return [self._kw("true")]
        if self._viene("false"):
            return [self._kw("false")]
        raise self._error(["true", "false"])

    # Sin contexto propio: un error aquí se entiende mejor atribuido a la
    # regla que contiene la coma opcional.
    @regla("ComaOpc", "R58", contexto=False)
    def _coma_opc(self):
        """<ComaOpc> ::= "," | ε. En toda la gramática va seguida de "}"."""
        if self._ver().kind is COMMA:
            return [self._t(COMMA)]
        if self._ver().kind is RBRACE:  # FOLLOW(ComaOpc)
            return []
        raise self._error([COMMA, RBRACE])
