"""Pruebas del analizador léxico (R59–R67)."""

import pytest

from chassis import LexError, TokenKind, tokenize

K = TokenKind


def resumen(texto):
    """Pares (clase, valor) de los tokens, sin el EOF final."""
    tokens = tokenize(texto)
    assert tokens[-1].kind is K.EOF
    return [(t.kind, t.value) for t in tokens[:-1]]


def test_entrada_vacia_solo_produce_eof():
    assert resumen("") == []
    assert resumen(" \t\n\n  ") == []


def test_puntuacion():
    assert resumen("{}[]:,") == [
        (K.LBRACE, "{"),
        (K.RBRACE, "}"),
        (K.LBRACKET, "["),
        (K.RBRACKET, "]"),
        (K.COLON, ":"),
        (K.COMMA, ","),
    ]


def test_cadena_guarda_el_contenido_sin_comillas():
    assert resumen('"hola mundo"') == [(K.STR, "hola mundo")]
    assert resumen('""') == [(K.STR, "")]


@pytest.mark.parametrize("palabra", ["mcps", "window-size", "dod-path", "a", "A1_b-2", "x-", "DB_USER"])
def test_palabra_usa_la_coincidencia_mas_larga(palabra):
    assert resumen(palabra) == [(K.WORD, palabra)]


def test_palabra_reservada_e_identificador():
    reservada, identificador, _ = tokenize("window-size docs")
    assert reservada.is_keyword
    assert not identificador.is_keyword


def test_los_tokens_no_necesitan_espacios_entre_si():
    assert resumen('a:"b",c') == [
        (K.WORD, "a"),
        (K.COLON, ":"),
        (K.STR, "b"),
        (K.COMMA, ","),
        (K.WORD, "c"),
    ]


def test_simbolos_de_r62_dentro_de_cadena():
    contenido = "{}[]':-_@/=,.* "
    assert resumen(f'"{contenido}"') == [(K.STR, contenido)]


@pytest.mark.parametrize("simbolo", list("?&#%+\\"))
def test_simbolos_anadidos_a_r62(simbolo):
    assert resumen(f'"a{simbolo}b"') == [(K.STR, f"a{simbolo}b")]


def test_url_con_consulta_y_fragmento():
    url = "https://x.dev/a%20b?q=1&r=2+3#frag"
    assert resumen(f'"{url}"') == [(K.STR, url)]


def test_la_barra_invertida_no_escapa():
    # "\" es un carácter más: la comilla siguiente cierra la cadena.
    assert resumen('"C:\\dir\\" x') == [(K.STR, "C:\\dir\\"), (K.WORD, "x")]


def test_posiciones():
    tokens = tokenize('mcps: {\n\t"a"\n}')
    donde = [(t.span.start.line, t.span.start.column) for t in tokens]
    assert donde == [(1, 1), (1, 5), (1, 7), (2, 2), (3, 1), (3, 2)]
    cadena = tokens[3]
    assert (cadena.span.end.line, cadena.span.end.column) == (2, 5)


@pytest.mark.parametrize("caracter", list('ñá!;()$~^<>|`') + ["\t"])
def test_caracter_fuera_del_alfabeto_en_cadena(caracter):
    with pytest.raises(LexError) as error:
        tokenize(f'"ab{caracter}cd"')
    assert "no permitido" in error.value.message
    assert (error.value.line, error.value.column) == (1, 4)
    assert error.value.rule == "<Car> (R61–R62)"


@pytest.mark.parametrize("texto", ['"abc', '"abc\n"', '"'])
def test_cadena_sin_cerrar(texto):
    with pytest.raises(LexError) as error:
        tokenize(texto)
    assert error.value.message == "cadena sin cerrar"
    assert (error.value.line, error.value.column) == (1, 1)


@pytest.mark.parametrize("texto", ["123", "1abc", "_x", "-y", "300k"])
def test_identificador_debe_empezar_por_letra(texto):
    with pytest.raises(LexError) as error:
        tokenize(texto)
    assert "debe empezar por una letra" in error.value.message
    assert error.value.rule == "<Id> (R63)"


@pytest.mark.parametrize("caracter", list("=.@*;()?&%+\\") + ["ñ"])
def test_caracter_inesperado_fuera_de_cadena(caracter):
    with pytest.raises(LexError) as error:
        tokenize(f"mcps {caracter}")
    assert "carácter inesperado" in error.value.message
    assert (error.value.line, error.value.column) == (1, 6)


def test_comillas_simples_sugieren_comillas_dobles():
    with pytest.raises(LexError) as error:
        tokenize("'hola'")
    assert "comillas dobles" in error.value.hint


@pytest.mark.parametrize("texto", ["// nota", "/* nota */", "# nota"])
def test_no_hay_comentarios(texto):
    with pytest.raises(LexError) as error:
        tokenize(texto)
    assert error.value.hint == "Chassis no admite comentarios"


def test_retorno_de_carro_no_es_espacio():
    # R67 solo admite "\n", "\t" y el espacio. Al leer un archivo, CRLF se
    # normaliza antes de llegar aquí.
    with pytest.raises(LexError) as error:
        tokenize("mcps\r\n")
    assert "retorno de carro" in error.value.message


def test_formato_del_error_senala_el_caracter():
    with pytest.raises(LexError) as error:
        tokenize('url: "año"', name="demo.chassis")
    lineas = error.value.format().splitlines()
    assert lineas[0] == "demo.chassis:1:8: error léxico en <Car> (R61–R62)"
    assert lineas[2] == '    url: "año"'
    assert lineas[3] == "           ^"
