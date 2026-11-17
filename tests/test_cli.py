"""Pruebas de la línea de comandos."""

import subprocess
import sys
from pathlib import Path

import pytest

from chassis.cli import main

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLO = RAIZ / "examples" / "ejemplo.chassis"
MINIMO = "mcps:{} skills:{} agents:{} loops:{}\n"


@pytest.fixture
def archivo(tmp_path):
    def crear(contenido, nombre="prueba.chassis"):
        ruta = tmp_path / nombre
        if isinstance(contenido, bytes):
            ruta.write_bytes(contenido)
        else:
            ruta.write_text(contenido, encoding="utf-8")
        return str(ruta)

    return crear


def test_archivo_valido(capsys):
    assert main([str(EJEMPLO)]) == 0
    salida = capsys.readouterr()
    assert salida.out.strip().endswith("sintaxis válida")
    assert salida.err == ""


def test_arbol_de_derivacion(capsys):
    assert main([str(EJEMPLO), "--tree"]) == 0
    esperado = (RAIZ / "tests" / "esperado" / "ejemplo.arbol.txt").read_text(encoding="utf-8")
    assert capsys.readouterr().out == esperado


def test_arbol_no_se_muestra_si_hay_error(archivo, capsys):
    assert main([archivo("mcps:{} skills:{} agents:{}\n"), "--tree"]) == 1
    assert capsys.readouterr().out == ""


def test_tokens(archivo, capsys):
    assert main([archivo('mcps: { "a b" }'), "--tokens"]) == 1  # los tokens salen aunque la sintaxis falle
    lineas = capsys.readouterr().out.splitlines()
    assert lineas == ["1:1\tWORD\tmcps", "1:5\tCOLON\t:", "1:7\tLBRACE\t{", "1:9\tSTR\ta b", "1:15\tRBRACE\t}", "1:16\tEOF\t"]


def test_error_sintactico(archivo, capsys):
    ruta = archivo("mcps:{} skills:{} agents:{}\n")
    assert main([ruta]) == 1
    salida = capsys.readouterr()
    assert salida.out == ""
    assert salida.err.startswith(f"{ruta}:2:1: error sintáctico en <SeccionLoops> (R44)")


def test_error_lexico(archivo, capsys):
    ruta = archivo('mcps:{ "ñ" }')
    assert main([ruta]) == 1
    assert capsys.readouterr().err.startswith(f"{ruta}:1:9: error léxico en <Car> (R61–R62)")


def test_archivo_inexistente(tmp_path, capsys):
    assert main([str(tmp_path / "no-existe.chassis")]) == 2
    assert "no se pudo leer" in capsys.readouterr().err


def test_archivo_que_no_es_utf8(archivo, capsys):
    assert main([archivo(b'mcps:{ "a\xf1o" }')]) == 2
    assert "UTF-8" in capsys.readouterr().err


def test_saltos_de_linea_de_windows(archivo):
    assert main([archivo(MINIMO.replace(" ", "\r\n").encode())]) == 0


def test_marca_bom(archivo):
    assert main([archivo(b"\xef\xbb\xbf" + MINIMO.encode())]) == 0


def test_python_m_chassis():
    resultado = subprocess.run(
        [sys.executable, "-m", "chassis", str(EJEMPLO)],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert resultado.returncode == 0
    assert "sintaxis válida" in resultado.stdout
