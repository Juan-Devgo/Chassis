"""Gramática de Chassis (R1–R58) escrita como tabla, tal como aparece en el
documento de reglas.

Es independiente del analizador: las pruebas la usan para comprobar que cada
nodo de un árbol de derivación aplica exactamente una de estas producciones.

Cada entrada es `no terminal: (regla, alternativas)`. Una alternativa es la
lista de símbolos del lado derecho; la lista vacía es ε. Los símbolos que no
son clave de la tabla son terminales: "Str", "Id" o el literal.
"""


def _lista(regla_lista, regla_cola, nombre, elemento):
    sufijo = nombre  # ListaX / ColaX
    return {
        f"Lista{sufijo}": (regla_lista, [[elemento, f"Cola{sufijo}"], []]),
        f"Cola{sufijo}": (regla_cola, [[",", f"Lista{sufijo}"], []]),
    }


def _cuerpo(campo, remota, local):
    return [
        ["remote", ",", campo, ":", "[", remota, "]", "ComaOpc"],
        ["local", ",", campo, ":", "[", local, "]", "ComaOpc"],
    ]


_REMOTO = [
    "command", ":", "Str", ",",
    "args", ":", "[", "ListaStr", "]", ",",
    "url", ":", "Str", ",",
    "options", ":", "[", "ListaStr", "]",
]
_COLA_AGENTE = [",", "model", ":", "Str", ",", "Permisos", ",", "window-size", ":", "Str", "ComaOpc", "}"]

GRAMATICA = {
    "Chassis": ("R1", [["SeccionMcps", "SeccionSkills", "SeccionAgents", "SeccionLoops"]]),
    # MCPs
    "SeccionMcps": ("R2", [["mcps", ":", "{", "ListaProvMcp", "}"]]),
    **_lista("R3", "R4", "ProvMcp", "ProvMcp"),
    "ProvMcp": ("R5", [["Str", ":", "{", "transport", ":", "CuerpoMcp", "}"]]),
    "CuerpoMcp": ("R6", _cuerpo("servers", "ListaSrvRemoto", "ListaSrvLocal")),
    **_lista("R7", "R8", "SrvRemoto", "SrvRemoto"),
    "SrvRemoto": ("R9", [["Str", ":", "{", "label", ":", "Str", ",", "url", ":", "Str", "OpcHeaders", "}"]]),
    "OpcHeaders": ("R10", [[",", "OpcHeadersCuerpo"], []]),
    "OpcHeadersCuerpo": ("R11", [["headers", ":", "{", "ListaPares", "}", "ComaOpc"], []]),
    **_lista("R12", "R13", "SrvLocal", "SrvLocal"),
    "SrvLocal": (
        "R14",
        [["Str", ":", "{", "label", ":", "Str", ",", "command", ":", "Str", ",",
          "args", ":", "[", "ListaStr", "]", "OpcEnv", "}"]],
    ),
    "OpcEnv": ("R15", [[",", "OpcEnvCuerpo"], []]),
    "OpcEnvCuerpo": ("R16", [["env", ":", "{", "ListaPares", "}", "ComaOpc"], []]),
    # Skills
    "SeccionSkills": ("R17", [["skills", ":", "{", "ListaProvSkill", "}"]]),
    **_lista("R18", "R19", "ProvSkill", "ProvSkill"),
    "ProvSkill": ("R20", [["Str", ":", "{", "access", ":", "CuerpoSkill", "}"]]),
    "CuerpoSkill": ("R21", _cuerpo("contexts", "ListaSkillRemota", "ListaSkillLocal")),
    **_lista("R22", "R23", "SkillRemota", "SkillRemota"),
    "SkillRemota": ("R24", [["Str", ":", "{", *_REMOTO, "ComaOpc", "}"]]),
    **_lista("R25", "R26", "SkillLocal", "SkillLocal"),
    "SkillLocal": ("R27", [["Str", ":", "{", "path", ":", "Str", "ComaOpc", "}"]]),
    # Agents
    "SeccionAgents": ("R28", [["agents", ":", "{", "ListaProvAgent", "}"]]),
    **_lista("R29", "R30", "ProvAgent", "ProvAgent"),
    "ProvAgent": ("R31", [["Str", ":", "{", "access", ":", "CuerpoAgent", "}"]]),
    "CuerpoAgent": ("R32", _cuerpo("contexts", "ListaAgentRemoto", "ListaAgentLocal")),
    **_lista("R33", "R34", "AgentRemoto", "AgentRemoto"),
    "AgentRemoto": ("R35", [["Str", ":", "{", *_REMOTO, *_COLA_AGENTE]]),
    **_lista("R36", "R37", "AgentLocal", "AgentLocal"),
    "AgentLocal": ("R38", [["Str", ":", "{", "path", ":", "Str", *_COLA_AGENTE]]),
    "Permisos": (
        "R39",
        [["permissions", ":", "{", "tools", ":", "Herramientas", ",",
          "files", ":", "[", "ListaArchivos", "]", "ComaOpc", "}"]],
    ),
    "Herramientas": ("R40", [["Str"], ["[", "ListaStr", "]"]]),
    **_lista("R41", "R42", "Archivos", "Archivo"),
    "Archivo": (
        "R43",
        [["Id", ":", "{", "on", ":", "Str", ",", "read", ":", "Bool", ",",
          "write", ":", "Bool", ",", "execute", ":", "Bool", "ComaOpc", "}"]],
    ),
    # Loops
    "SeccionLoops": ("R44", [["loops", ":", "{", "ListaLoop", "}"]]),
    **_lista("R45", "R46", "Loop", "Loop"),
    "Loop": (
        "R47",
        [["Str", ":", "{", "coordinator-agent", ":", "Str", ",",
          "subagents", ":", "[", "ListaStr", "]", ",",
          "principles-path", ":", "Str", ",",
          "steps", ":", "[", "ListaPaso", "]", ",",
          "dod-path", ":", "Str", "ComaOpc", "}"]],
    ),
    **_lista("R48", "R49", "Paso", "Paso"),
    "Paso": (
        "R50",
        [["Str", ":", "{", "agents", ":", "[", "ListaStr", "]", ",", "context-path", ":", "Str", "ComaOpc", "}"]],
    ),
    # Comunes
    **_lista("R51", "R52", "Str", "Str"),
    **_lista("R53", "R54", "Pares", "Par"),
    "Par": ("R55", [["Clave", ":", "Str"]]),
    "Clave": ("R56", [["Id"], ["Str"]]),
    "Bool": ("R57", [["true"], ["false"]]),
    "ComaOpc": ("R58", [[","], []]),
}

assert len(GRAMATICA) == 58
assert sorted(int(regla[1:]) for regla, _ in GRAMATICA.values()) == list(range(1, 59))
