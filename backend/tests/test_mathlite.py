"""Suite de pruebas automatizadas de MathLite — Fase 6.

Cubre las cinco fases del intérprete con casos positivos y negativos:
  * Léxico   (errores de carácter inválido y cadena sin cerrar)
  * Sintáctico (paréntesis sin cerrar, función sin bloque, if sin condición)
  * Semántico (SE001–SE008)
  * Ejecución (división por cero, función no definida, resultados correctos)

Se ejecuta con:  pytest -v
"""
from __future__ import annotations

from mathlite.service import analyze_source


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(source: str) -> dict:
    return analyze_source(source)


def sem_codes(result: dict) -> set[str]:
    return {e["code"] for e in result["semantic_errors"]}


def rt_codes(result: dict) -> set[str]:
    return {e["code"] for e in result["runtime_errors"]}


# ===========================================================================
# 1. PROGRAMAS VÁLIDOS  (casos positivos — sección 6.1 del enunciado)
# ===========================================================================

def test_01_aritmetica_precedencia():
    """(3 + 4 * 2) / (1 - 5)^2  ->  11/16 = 0.6875"""
    r = run("let x = (3 + 4 * 2) / (1 - 5) ^ 2\nprint(x)")
    assert r["ok"]
    assert r["output"] == ["0.6875"]


def test_02_factorial_recursivo():
    src = """
def factorial(n) {
  if n <= 1 { return 1 }
  return n * factorial(n - 1)
}
print(factorial(5))
"""
    r = run(src)
    assert r["ok"]
    assert r["output"] == ["120"]


def test_03_while_acumulador():
    """Suma de 1 a 10 = 55"""
    src = """
let suma = 0
let i = 1
while i <= 10 {
  let suma = suma + i
  let i = i + 1
}
print(suma)
"""
    r = run(src)
    assert r["ok"]
    assert r["output"] == ["55"]


def test_04_funciones_trigonometricas():
    """sqrt y abs en una expresión compuesta -> sqrt(abs(-16)) = 4.0"""
    r = run("let y = sqrt(abs(-16.0))\nprint(y)")
    assert r["ok"]
    assert r["output"] == ["4.0"]


def test_05_funcion_llama_a_funcion():
    """hipotenusa(3,4) = sqrt(cuadrado(3)+cuadrado(4)) = 5.0"""
    src = """
def cuadrado(x) { return x * x }
def hipotenusa(a, b) { return sqrt(cuadrado(a) + cuadrado(b)) }
print(hipotenusa(3, 4))
"""
    r = run(src)
    assert r["ok"]
    assert r["output"] == ["5.0"]


def test_06_if_else():
    src = """
let x = 7
if x > 5 { print(x) } else { print(0) }
"""
    r = run(src)
    assert r["ok"]
    assert r["output"] == ["7"]


def test_07_booleanos_y_logicos():
    src = """
let a = true
let b = false
if a and not b { print(1) }
"""
    r = run(src)
    assert r["ok"]
    assert r["output"] == ["1"]


def test_08_concatenacion_strings():
    r = run('let s = "hola" + "mundo"\nprint(s)')
    assert r["ok"]
    assert r["output"] == ["holamundo"]


def test_09_modulo_y_potencia():
    r = run("print(10 % 3)\nprint(2 ^ 5)")
    assert r["ok"]
    assert r["output"] == ["1", "32"]


def test_10_promocion_int_real():
    """Int op Real -> Real"""
    r = run("let x = 5 + 2.0\nprint(x)")
    assert r["ok"]
    assert r["output"] == ["7.0"]


def test_11_builtins_floor_ceil():
    r = run("print(floor(3.7))\nprint(ceil(3.2))")
    assert r["ok"]
    assert r["output"] == ["3", "4"]


def test_12_comentarios_ignorados():
    src = """
-- esto es un comentario
let x = 5  -- otro comentario
print(x)
"""
    r = run(src)
    assert r["ok"]
    assert r["output"] == ["5"]


# ===========================================================================
# 2. ERRORES LÉXICOS  (sección 6.2)
# ===========================================================================

def test_13_caracter_invalido():
    r = run("let x = @5")
    assert not r["ok"]
    assert len(r["lexer_errors"]) >= 1


def test_14_cadena_sin_cerrar():
    r = run('let s = "hola')
    assert not r["ok"]
    assert len(r["lexer_errors"]) >= 1


def test_15_lexico_no_aborta():
    """Un error léxico no debe impedir tokenizar el resto."""
    r = run("let x = @\nlet y = 5")
    assert len(r["lexer_errors"]) >= 1
    # 'y' debe haberse tokenizado pese al error previo
    lexemas = [t["lexeme"] for t in r["tokens"]]
    assert "y" in lexemas


# ===========================================================================
# 3. ERRORES SINTÁCTICOS  (sección 6.3)
# ===========================================================================

def test_16_parentesis_sin_cerrar():
    r = run("let x = (3 + 4 * 2")
    assert not r["ok"]
    assert len(r["parser_errors"]) >= 1


def test_17_funcion_sin_bloque():
    r = run("def f(x) return x")
    assert not r["ok"]
    assert len(r["parser_errors"]) >= 1


def test_18_if_sin_condicion():
    r = run("if { print(1) }")
    assert not r["ok"]
    assert len(r["parser_errors"]) >= 1


# ===========================================================================
# 4. ERRORES SEMÁNTICOS  (sección 6.4 — SE001..SE008)
# ===========================================================================

def test_19_variable_no_declarada():
    r = run("print(noDeclarada)")
    assert "SE001" in sem_codes(r)


def test_20_funcion_duplicada():
    """SE002 (redeclaración) se conserva para funciones."""
    r = run("def f(x) { return x }\ndef f(y) { return y }")
    assert "SE002" in sem_codes(r)


def test_21_funcion_no_definida():
    r = run("print(noExiste(5))")
    assert "SE003" in sem_codes(r)


def test_22_aridad_incorrecta():
    src = """
def suma(a, b) { return a + b }
print(suma(1))
"""
    r = run(src)
    assert "SE004" in sem_codes(r)


def test_23_tipos_incompatibles():
    """String + Int -> SE005"""
    r = run('let x = "hola" + 5')
    assert "SE005" in sem_codes(r)


def test_24_return_fuera_de_funcion():
    r = run("return 99")
    assert "SE006" in sem_codes(r)


# ===========================================================================
# 5. ERRORES EN TIEMPO DE EJECUCIÓN  (sección 6.5)
# ===========================================================================

def test_25_division_por_cero():
    r = run("let r = 10 / 0\nprint(r)")
    assert "RE001" in rt_codes(r)
