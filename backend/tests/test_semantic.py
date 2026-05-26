"""Tests de la Fase 4 — Análisis Semántico de MathLite.

Cubre las 8 categorías de error definidas en SemanticError:
  SE001 – variable no declarada
  SE002 – redeclaración de variable en el mismo alcance
  SE003 – función no definida
  SE004 – aridad incorrecta en llamada a función
  SE005 – tipo incompatible en operación aritmética
  SE006 – return fuera del cuerpo de una función
  SE007 – operador lógico / 'not' aplicado a tipo no booleano
  SE008 – condición de if/while no es booleana

También se verifica que el análisis semántico:
  - Infiera correctamente los tipos (Int, Real, String, Bool).
  - Permita programas válidos sin generar errores.
  - Integre coherentemente con el pipeline completo (service.analyze_source).
"""
from __future__ import annotations

import pytest

from mathlite.lexer import Lexer
from mathlite.parser import Parser
from mathlite.semantic import (
    TYPE_BOOL,
    TYPE_INT,
    TYPE_REAL,
    TYPE_STRING,
    SemanticAnalyzer,
    analyze_semantics,
)
from mathlite.service import analyze_source


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _analyze(source: str):
    """Devuelve (errors, symbol_table) a partir de código fuente."""
    tokens, _ = Lexer(source).scan_tokens()
    program = Parser(tokens).parse()
    return analyze_semantics(program)


def _codes(source: str) -> list[str]:
    """Devuelve solo los códigos de error semántico."""
    errors, _ = _analyze(source)
    return [e.code for e in errors]


def _no_errors(source: str) -> None:
    errors, _ = _analyze(source)
    assert errors == [], f"Se esperaban 0 errores, pero se obtuvieron: {errors}"


# ===========================================================================
# 1. Programas válidos — sin errores
# ===========================================================================

class TestValidPrograms:
    def test_simple_assignment_and_print(self):
        _no_errors("let x = 42\nprint(x)\n")

    def test_int_arithmetic(self):
        _no_errors("let a = 3\nlet b = 4\nlet c = a + b\n")

    def test_real_arithmetic(self):
        _no_errors("let a = 1.5\nlet b = 2.0\nlet c = a * b\n")

    def test_int_real_promotion(self):
        _no_errors("let a = 3\nlet b = 1.5\nlet c = a + b\n")

    def test_boolean_logic(self):
        _no_errors("let x = true\nlet y = false\nlet z = x and y\n")

    def test_string_concatenation(self):
        _no_errors('let s = "hola" + " mundo"\n')

    def test_function_definition_and_call(self):
        _no_errors("def area(b, h) {\n  return b * h\n}\nlet r = area(3, 4)\n")

    def test_if_with_bool_condition(self):
        _no_errors("let x = true\nif x {\n  let y = 1\n}\n")

    def test_while_with_bool_condition(self):
        _no_errors("let ok = true\nwhile ok {\n  let k = 0\n}\n")

    def test_nested_function_calls(self):
        _no_errors("def doble(x) {\n  return x * 2\n}\nlet r = doble(doble(5))\n")

    def test_builtin_function_call(self):
        _no_errors("let r = sqrt(16.0)\n")

    def test_comparison_returns_bool(self):
        _no_errors("let a = 3\nlet b = 4\nlet c = a < b\nif c {\n  let d = 1\n}\n")


# ===========================================================================
# SE001 – Variable no declarada antes de su uso
# ===========================================================================

class TestSE001_UndeclaredVariable:
    def test_undeclared_in_expression(self):
        assert "SE001" in _codes("let a = x + 1\n")

    def test_undeclared_in_print(self):
        assert "SE001" in _codes("print(noExiste)\n")

    def test_undeclared_after_function(self):
        src = "def f(n) {\n  return n + 1\n}\nlet r = fantasma\n"
        assert "SE001" in _codes(src)

    def test_declared_then_ok(self):
        _no_errors("let x = 10\nlet y = x + 1\n")

    def test_message_contains_variable_name(self):
        errors, _ = _analyze("print(mivariable)\n")
        se001 = [e for e in errors if e.code == "SE001"]
        assert se001, "Debe haber al menos un SE001"
        assert "mivariable" in se001[0].message


# ===========================================================================
# SE002 – Redeclaración de variable en el mismo alcance
# ===========================================================================

class TestSE002_Redeclaration:
    def test_redeclaration_global(self):
        assert "SE002" in _codes("let x = 1\nlet x = 2\n")

    def test_redeclaration_inside_function(self):
        src = "def f(n) {\n  let y = 1\n  let y = 2\n  return y\n}\n"
        assert "SE002" in _codes(src)

    def test_shadow_from_outer_scope_is_allowed(self):
        # Variable global 'x' puede declararse también en la función
        src = "let x = 10\ndef f() {\n  let x = 99\n  return x\n}\n"
        errors = [e for e in _analyze(src)[0] if e.code == "SE002"]
        assert errors == [], "Sombreado desde alcance externo debe estar permitido"

    def test_redeclaration_message_descriptive(self):
        errors, _ = _analyze("let val = 5\nlet val = 6\n")
        se002 = [e for e in errors if e.code == "SE002"]
        assert se002
        assert "val" in se002[0].message


# ===========================================================================
# SE003 – Función no definida
# ===========================================================================

class TestSE003_UndefinedFunction:
    def test_call_undefined_function(self):
        assert "SE003" in _codes("let r = noExiste(1, 2)\n")

    def test_call_defined_function_ok(self):
        _no_errors("def suma(a, b) {\n  return a + b\n}\nlet r = suma(1, 2)\n")

    def test_message_contains_function_name(self):
        errors, _ = _analyze("let r = miFuncion()\n")
        se003 = [e for e in errors if e.code == "SE003"]
        assert se003
        assert "miFuncion" in se003[0].message

    def test_builtin_not_flagged_as_undefined(self):
        errors = [e for e in _analyze("let r = sqrt(4.0)\n")[0] if e.code == "SE003"]
        assert errors == []


# ===========================================================================
# SE004 – Aridad incorrecta
# ===========================================================================

class TestSE004_ArityMismatch:
    def test_too_few_args(self):
        src = "def suma(a, b) {\n  return a + b\n}\nlet r = suma(1)\n"
        assert "SE004" in _codes(src)

    def test_too_many_args(self):
        src = "def suma(a, b) {\n  return a + b\n}\nlet r = suma(1, 2, 3)\n"
        assert "SE004" in _codes(src)

    def test_correct_arity_ok(self):
        _no_errors("def f(x) {\n  return x\n}\nlet r = f(5)\n")

    def test_message_shows_expected_and_provided(self):
        src = "def f(x, y) {\n  return x\n}\nlet r = f(1)\n"
        errors, _ = _analyze(src)
        se004 = [e for e in errors if e.code == "SE004"]
        assert se004
        assert "2" in se004[0].message  # esperaba 2
        assert "1" in se004[0].message  # se dieron 1


# ===========================================================================
# SE005 – Tipo incompatible en operación aritmética
# ===========================================================================

class TestSE005_TypeIncompatibility:
    def test_string_plus_int(self):
        assert "SE005" in _codes('let r = "hola" + 3\n')

    def test_string_minus_string(self):
        assert "SE005" in _codes('let r = "a" - "b"\n')

    def test_bool_times_int(self):
        assert "SE005" in _codes("let r = true * 3\n")

    def test_int_plus_real_ok(self):
        _no_errors("let r = 3 + 1.5\n")

    def test_string_concat_ok(self):
        _no_errors('let r = "hello" + " world"\n')

    def test_comparison_numeric_ok(self):
        _no_errors("let r = 3 < 4\n")

    def test_int_modulo_int_ok(self):
        _no_errors("let r = 10 % 3\n")

    def test_unary_minus_string(self):
        assert "SE005" in _codes('let r = -"hola"\n')


# ===========================================================================
# SE006 – return fuera de función
# ===========================================================================

class TestSE006_ReturnOutsideFunction:
    def test_return_at_global_scope(self):
        assert "SE006" in _codes("return 42\n")

    def test_return_inside_function_ok(self):
        _no_errors("def f(x) {\n  return x * 2\n}\n")

    def test_return_message_descriptive(self):
        errors, _ = _analyze("return 0\n")
        se006 = [e for e in errors if e.code == "SE006"]
        assert se006
        assert "return" in se006[0].message.lower()


# ===========================================================================
# SE007 – Operador lógico / 'not' sobre tipo no booleano
# ===========================================================================

class TestSE007_LogicalTypeMismatch:
    def test_int_and_int(self):
        assert "SE007" in _codes("let r = 1 and 0\n")

    def test_string_or_bool(self):
        assert "SE007" in _codes('let r = "si" or true\n')

    def test_not_int(self):
        assert "SE007" in _codes("let r = not 5\n")

    def test_bool_and_bool_ok(self):
        _no_errors("let r = true and false\n")

    def test_not_bool_ok(self):
        _no_errors("let r = not true\n")


# ===========================================================================
# SE008 – Condición de if/while no es booleana
# ===========================================================================

class TestSE008_NonBooleanCondition:
    def test_if_with_int_condition(self):
        assert "SE008" in _codes("if 1 {\n  let x = 0\n}\n")

    def test_if_with_string_condition(self):
        assert "SE008" in _codes('if "yes" {\n  let x = 0\n}\n')

    def test_while_with_int_condition(self):
        assert "SE008" in _codes("while 1 {\n  let x = 0\n}\n")

    def test_if_with_bool_literal_ok(self):
        _no_errors("if true {\n  let x = 1\n}\n")

    def test_while_with_comparison_ok(self):
        _no_errors("let a = 0\nwhile a < 10 {\n  let b = 1\n}\n")


# ===========================================================================
# Inferencia de tipos
# ===========================================================================

class TestTypeInference:
    def test_int_literal_inferred(self):
        tokens, _ = Lexer("let x = 42\n").scan_tokens()
        program = Parser(tokens).parse()
        analyze_semantics(program)
        assign = program.statements[0]
        assert assign.inferred_type == TYPE_INT

    def test_real_literal_inferred(self):
        tokens, _ = Lexer("let x = 3.14\n").scan_tokens()
        program = Parser(tokens).parse()
        analyze_semantics(program)
        assign = program.statements[0]
        assert assign.inferred_type == TYPE_REAL

    def test_string_literal_inferred(self):
        tokens, _ = Lexer('let s = "hola"\n').scan_tokens()
        program = Parser(tokens).parse()
        analyze_semantics(program)
        assign = program.statements[0]
        assert assign.inferred_type == TYPE_STRING

    def test_bool_literal_inferred(self):
        tokens, _ = Lexer("let b = true\n").scan_tokens()
        program = Parser(tokens).parse()
        analyze_semantics(program)
        assign = program.statements[0]
        assert assign.inferred_type == TYPE_BOOL

    def test_int_plus_real_is_real(self):
        tokens, _ = Lexer("let r = 3 + 1.5\n").scan_tokens()
        program = Parser(tokens).parse()
        analyze_semantics(program)
        assign = program.statements[0]
        assert assign.inferred_type == TYPE_REAL

    def test_comparison_is_bool(self):
        tokens, _ = Lexer("let b = 3 < 5\n").scan_tokens()
        program = Parser(tokens).parse()
        analyze_semantics(program)
        assign = program.statements[0]
        assert assign.inferred_type == TYPE_BOOL


# ===========================================================================
# Integración con el pipeline completo (service.analyze_source)
# ===========================================================================

class TestServiceIntegration:
    def test_valid_program_ok_true(self):
        src = "let x = 3 + 4\nprint(x)\n"
        result = analyze_source(src)
        assert result["ok"] is True
        assert result["semantic_errors"] == []

    def test_semantic_error_makes_ok_false(self):
        result = analyze_source("print(noDeclarada)\n")
        assert result["ok"] is False
        assert any(e["code"] == "SE001" for e in result["semantic_errors"])

    def test_symbol_table_in_response(self):
        result = analyze_source("let x = 10\nlet y = 20.5\n")
        st = result["symbol_table"]
        names = {v["name"] for v in st["variables"]}
        assert "x" in names
        assert "y" in names

    def test_function_in_symbol_table(self):
        result = analyze_source("def suma(a, b) {\n  return a + b\n}\n")
        funcs = result["symbol_table"]["functions"]
        assert any(f["name"] == "suma" for f in funcs)

    def test_semantic_errors_include_line(self):
        result = analyze_source("let r = sinDefinir\n")
        se = result["semantic_errors"]
        assert se
        assert "line" in se[0]
        assert se[0]["line"] >= 1

    def test_full_program_example(self):
        src = (
            "let base = 5\n"
            "let altura = 3.0\n"
            "def area(b, h) {\n"
            "  return (b * h) / 2\n"
            "}\n"
            "let resultado = area(base, altura)\n"
            "print(resultado)\n"
        )
        result = analyze_source(src)
        assert result["ok"] is True, f"Errores: {result['semantic_errors']}"
