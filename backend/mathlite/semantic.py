"""mathlite.semantic — Fase 4: Análisis Semántico
=================================================
Recorre el AST producido por el parser y:

* Mantiene una tabla de símbolos con dos alcances (global / función).
* Infiere el tipo de cada nodo y lo anota en ``node.inferred_type``.
* Detecta y acumula errores semánticos sin abortar el recorrido.

Tipos del sistema
-----------------
  "Int"    – número entero  (NumberNode con valor int)
  "Real"   – número real    (NumberNode con valor float)
  "String" – cadena
  "Bool"   – booleano
  "Void"   – sin valor (return vacío, sentencias)
  "Any"    – tipo desconocido / parámetro sin anotación

Reglas de compatibilidad aritmética
------------------------------------
  Int  op Int    → Int
  Int  op Real   → Real   (promoción)
  Real op Int    → Real
  Real op Real   → Real
  String op *    → ERROR  (SE005)
  Bool op *      → ERROR  (SE005) — excepto ==, !=
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .ast import (
    AssignNode,
    BinOpNode,
    BlockNode,
    BoolNode,
    ExpressionStmtNode,
    FuncCallNode,
    FuncDefNode,
    IfNode,
    Node,
    NumberNode,
    PrintNode,
    ProgramNode,
    ReturnNode,
    StringNode,
    UnaryOpNode,
    VariableNode,
    WhileNode,
)
from .errors import SemanticError

# ---------------------------------------------------------------------------
# Tipos internos
# ---------------------------------------------------------------------------

TYPE_INT = "Int"
TYPE_REAL = "Real"
TYPE_STRING = "String"
TYPE_BOOL = "Bool"
TYPE_VOID = "Void"
TYPE_ANY = "Any"

NUMERIC_TYPES = {TYPE_INT, TYPE_REAL}
ARITHMETIC_OPS = {"+", "-", "*", "/", "^", "%"}
COMPARISON_OPS = {"==", "!=", "<", ">", "<=", ">="}
LOGICAL_OPS = {"and", "or"}

# Operadores matemáticos de la lib (sin ataques externos)
BUILTIN_TYPES: dict[str, str] = {
    "sin": TYPE_REAL,
    "cos": TYPE_REAL,
    "tan": TYPE_REAL,
    "sqrt": TYPE_REAL,
    "log": TYPE_REAL,
    "abs": TYPE_REAL,
    "floor": TYPE_INT,
    "ceil": TYPE_INT,
}


# ---------------------------------------------------------------------------
# Tabla de símbolos
# ---------------------------------------------------------------------------

@dataclass
class SymbolInfo:
    name: str
    sym_type: str          # tipo inferido de la variable
    line: int              # línea de declaración


@dataclass
class FunctionInfo:
    name: str
    param_names: list[str]
    line: int


@dataclass
class SymbolTable:
    """Tabla de símbolos de dos alcances: global y función activa."""

    _globals: dict[str, SymbolInfo] = field(default_factory=dict)
    _locals: Optional[dict[str, SymbolInfo]] = field(default=None)
    _functions: dict[str, FunctionInfo] = field(default_factory=dict)

    # ---- Alcance de variables ----

    def enter_function(self) -> None:
        self._locals = {}

    def exit_function(self) -> None:
        self._locals = None

    def in_function(self) -> bool:
        return self._locals is not None

    def declare_variable(self, name: str, sym_type: str, line: int) -> bool:
        """Declara la variable en el alcance actual.
        Devuelve False si ya existía en ese mismo alcance (redeclaración)."""
        scope = self._locals if self._locals is not None else self._globals
        if name in scope:
            return False
        scope[name] = SymbolInfo(name=name, sym_type=sym_type, line=line)
        return True

    def lookup_variable(self, name: str) -> Optional[SymbolInfo]:
        """Busca primero en locales, luego en globales."""
        if self._locals is not None and name in self._locals:
            return self._locals[name]
        return self._globals.get(name)

    def update_variable_type(self, name: str, sym_type: str) -> None:
        """Actualiza el tipo de una variable ya declarada."""
        if self._locals is not None and name in self._locals:
            self._locals[name].sym_type = sym_type
        elif name in self._globals:
            self._globals[name].sym_type = sym_type

    # ---- Alcance de funciones ----

    def declare_function(self, name: str, params: list[str], line: int) -> bool:
        if name in self._functions:
            return False
        self._functions[name] = FunctionInfo(name=name, param_names=params, line=line)
        return True

    def lookup_function(self, name: str) -> Optional[FunctionInfo]:
        return self._functions.get(name)


# ---------------------------------------------------------------------------
# Analizador semántico
# ---------------------------------------------------------------------------

class SemanticAnalyzer:
    """Recorre el AST, anota tipos y acumula errores semánticos."""

    def __init__(self) -> None:
        self.errors: list[SemanticError] = []
        self.symbols = SymbolTable()
        self._in_function = False  # Para detectar return fuera de función

    # ------------------------------------------------------------------ #
    #  Punto de entrada                                                    #
    # ------------------------------------------------------------------ #

    def analyze(self, program: ProgramNode) -> list[SemanticError]:
        """Analiza el programa completo y devuelve la lista de errores."""
        self.errors = []
        self.symbols = SymbolTable()
        self._in_function = False

        # Primer pase: registrar todas las funciones definidas en el ámbito
        # global para permitir llamadas "hacia adelante" dentro de bloques.
        for stmt in program.statements:
            if isinstance(stmt, FuncDefNode):
                self._register_function(stmt)

        # Segundo pase: analizar todo
        for stmt in program.statements:
            self._visit(stmt)

        return self.errors

    # ------------------------------------------------------------------ #
    #  Registro previo de funciones (primer pase)                         #
    # ------------------------------------------------------------------ #

    def _register_function(self, node: FuncDefNode) -> None:
        ok = self.symbols.declare_function(node.name, node.params, node.line)
        if not ok:
            self._error(
                "SE002",
                f"La función '{node.name}' ya fue definida en este alcance.",
                node.line,
            )

    # ------------------------------------------------------------------ #
    #  Dispatcher principal                                               #
    # ------------------------------------------------------------------ #

    def _visit(self, node: Node | None) -> str:
        """Visita un nodo y devuelve su tipo inferido."""
        if node is None:
            return TYPE_VOID

        if isinstance(node, ProgramNode):
            return self._visit_program(node)
        if isinstance(node, BlockNode):
            return self._visit_block(node)
        if isinstance(node, AssignNode):
            return self._visit_assign(node)
        if isinstance(node, FuncDefNode):
            return self._visit_func_def(node)
        if isinstance(node, FuncCallNode):
            return self._visit_func_call(node)
        if isinstance(node, IfNode):
            return self._visit_if(node)
        if isinstance(node, WhileNode):
            return self._visit_while(node)
        if isinstance(node, PrintNode):
            return self._visit_print(node)
        if isinstance(node, ReturnNode):
            return self._visit_return(node)
        if isinstance(node, ExpressionStmtNode):
            return self._visit_expr_stmt(node)
        if isinstance(node, BinOpNode):
            return self._visit_binop(node)
        if isinstance(node, UnaryOpNode):
            return self._visit_unary(node)
        if isinstance(node, NumberNode):
            return self._visit_number(node)
        if isinstance(node, StringNode):
            return self._visit_string(node)
        if isinstance(node, BoolNode):
            return self._visit_bool(node)
        if isinstance(node, VariableNode):
            return self._visit_variable(node)

        # Nodo desconocido — no hay tipo
        self._annotate(node, TYPE_ANY)
        return TYPE_ANY

    # ------------------------------------------------------------------ #
    #  Visitores por nodo                                                 #
    # ------------------------------------------------------------------ #

    def _visit_program(self, node: ProgramNode) -> str:
        for stmt in node.statements:
            self._visit(stmt)
        self._annotate(node, TYPE_VOID)
        return TYPE_VOID

    def _visit_block(self, node: BlockNode) -> str:
        for stmt in node.statements:
            self._visit(stmt)
        self._annotate(node, TYPE_VOID)
        return TYPE_VOID

    # ---- Declaración / asignación ----

    def _visit_assign(self, node: AssignNode) -> str:
        value_type = self._visit(node.value)

        already_declared = self.symbols.lookup_variable(node.name)

        if already_declared is not None:
            # --- SE002: redeclaración en el mismo alcance ---
            # Determinar alcance actual para comparar
            current_scope = (
                self.symbols._locals
                if self.symbols._locals is not None
                else self.symbols._globals
            )
            if node.name in current_scope:
                self._error(
                    "SE002",
                    f"La variable '{node.name}' ya fue declarada en este alcance "
                    f"(línea {already_declared.line}). Usa una asignación simple.",
                    node.line,
                )
            else:
                # Reasignación desde alcance externo: permitida, actualiza tipo
                self.symbols.update_variable_type(node.name, value_type)
        else:
            self.symbols.declare_variable(node.name, value_type, node.line)

        self._annotate(node, value_type)
        return value_type

    # ---- Definición de función ----

    def _visit_func_def(self, node: FuncDefNode) -> str:
        # La función ya fue registrada en el primer pase; aquí analizamos el cuerpo.
        self.symbols.enter_function()
        prev_in_function = self._in_function
        self._in_function = True

        # Declarar parámetros como variables locales con tipo Any (sin anotación)
        for param in node.params:
            self.symbols.declare_variable(param, TYPE_ANY, node.line)

        self._visit(node.body)

        self._in_function = prev_in_function
        self.symbols.exit_function()
        self._annotate(node, TYPE_VOID)
        return TYPE_VOID

    # ---- Llamada a función ----

    def _visit_func_call(self, node: FuncCallNode) -> str:
        # Evaluar argumentos primero
        arg_types = [self._visit(arg) for arg in node.args]

        # Builtin functions (sin, cos, sqrt, …)
        if node.callee in BUILTIN_TYPES:
            ret_type = BUILTIN_TYPES[node.callee]
            self._annotate(node, ret_type)
            return ret_type

        # --- SE003: función no definida ---
        func_info = self.symbols.lookup_function(node.callee)
        if func_info is None:
            self._error(
                "SE003",
                f"La función '{node.callee}' no está definida.",
                node.line,
            )
            self._annotate(node, TYPE_ANY)
            return TYPE_ANY

        # --- SE004: número de argumentos incorrecto ---
        expected = len(func_info.param_names)
        provided = len(node.args)
        if expected != provided:
            self._error(
                "SE004",
                f"La función '{node.callee}' espera {expected} argumento(s), "
                f"pero se proporcionaron {provided}.",
                node.line,
            )

        self._annotate(node, TYPE_ANY)  # Tipo de retorno desconocido sin anotaciones
        return TYPE_ANY

    # ---- Control de flujo ----

    def _visit_if(self, node: IfNode) -> str:
        cond_type = self._visit(node.condition)

        # --- SE008: condición no booleana ---
        if cond_type not in (TYPE_BOOL, TYPE_ANY):
            self._error(
                "SE008",
                f"La condición del 'if' debe ser de tipo Bool, pero se encontró '{cond_type}'.",
                node.line,
            )

        self._visit(node.then_branch)
        if node.else_branch is not None:
            self._visit(node.else_branch)

        self._annotate(node, TYPE_VOID)
        return TYPE_VOID

    def _visit_while(self, node: WhileNode) -> str:
        cond_type = self._visit(node.condition)

        # --- SE008: condición no booleana ---
        if cond_type not in (TYPE_BOOL, TYPE_ANY):
            self._error(
                "SE008",
                f"La condición del 'while' debe ser de tipo Bool, pero se encontró '{cond_type}'.",
                node.line,
            )

        self._visit(node.body)
        self._annotate(node, TYPE_VOID)
        return TYPE_VOID

    def _visit_print(self, node: PrintNode) -> str:
        self._visit(node.value)
        self._annotate(node, TYPE_VOID)
        return TYPE_VOID

    def _visit_return(self, node: ReturnNode) -> str:
        # --- SE006: return fuera de función ---
        if not self._in_function:
            self._error(
                "SE006",
                "La sentencia 'return' está fuera del cuerpo de una función.",
                node.line,
            )

        ret_type = self._visit(node.value)
        self._annotate(node, ret_type)
        return ret_type

    def _visit_expr_stmt(self, node: ExpressionStmtNode) -> str:
        t = self._visit(node.expression)
        self._annotate(node, t)
        return t

    # ---- Expresiones ----

    def _visit_binop(self, node: BinOpNode) -> str:
        left_type = self._visit(node.left)
        right_type = self._visit(node.right)
        result_type = self._infer_binop_type(node, left_type, right_type)
        self._annotate(node, result_type)
        return result_type

    def _infer_binop_type(self, node: BinOpNode, left: str, right: str) -> str:
        op = node.op

        # --- Operadores lógicos (and / or) ---
        if op in LOGICAL_OPS:
            # SE007: operandos no booleanos
            if left not in (TYPE_BOOL, TYPE_ANY):
                self._error(
                    "SE007",
                    f"El operando izquierdo de '{op}' debe ser Bool, pero se encontró '{left}'.",
                    node.line,
                )
            if right not in (TYPE_BOOL, TYPE_ANY):
                self._error(
                    "SE007",
                    f"El operando derecho de '{op}' debe ser Bool, pero se encontró '{right}'.",
                    node.line,
                )
            return TYPE_BOOL

        # --- Operadores de comparación ---
        if op in COMPARISON_OPS:
            # Comparaciones ==, != son válidas entre tipos iguales o mixtos numéricos
            if op in ("==", "!="):
                return TYPE_BOOL
            # <, >, <=, >= solo para numéricos
            if left in NUMERIC_TYPES and right in NUMERIC_TYPES:
                return TYPE_BOOL
            if left == TYPE_ANY or right == TYPE_ANY:
                return TYPE_BOOL
            self._error(
                "SE005",
                f"El operador '{op}' no es aplicable a los tipos '{left}' y '{right}'.",
                node.line,
            )
            return TYPE_BOOL

        # --- Operadores aritméticos ---
        if op in ARITHMETIC_OPS:
            # Tipo Any pasa sin error (parámetro desconocido)
            if left == TYPE_ANY or right == TYPE_ANY:
                return TYPE_ANY

            # SE005: tipos incompatibles
            if left == TYPE_STRING or right == TYPE_STRING:
                # Excepción: String + String es concatenación válida
                if op == "+" and left == TYPE_STRING and right == TYPE_STRING:
                    return TYPE_STRING
                self._error(
                    "SE005",
                    f"El operador '{op}' no es aplicable entre tipos '{left}' y '{right}'. "
                    f"String solo puede concatenarse con otro String mediante '+'.",
                    node.line,
                )
                return TYPE_ANY

            if left == TYPE_BOOL or right == TYPE_BOOL:
                self._error(
                    "SE005",
                    f"El operador '{op}' no es aplicable a tipo Bool.",
                    node.line,
                )
                return TYPE_ANY

            # Int op Real → Real; Int op Int → Int; Real op Real → Real
            if TYPE_REAL in (left, right):
                return TYPE_REAL
            return TYPE_INT

        return TYPE_ANY

    def _visit_unary(self, node: UnaryOpNode) -> str:
        operand_type = self._visit(node.operand)
        if node.op == "-":
            if operand_type not in NUMERIC_TYPES and operand_type != TYPE_ANY:
                self._error(
                    "SE005",
                    f"El operador unario '-' no es aplicable al tipo '{operand_type}'.",
                    node.line,
                )
                self._annotate(node, TYPE_ANY)
                return TYPE_ANY
            self._annotate(node, operand_type)
            return operand_type
        if node.op == "not":
            if operand_type not in (TYPE_BOOL, TYPE_ANY):
                self._error(
                    "SE007",
                    f"El operador 'not' requiere un operando Bool, pero se encontró '{operand_type}'.",
                    node.line,
                )
            self._annotate(node, TYPE_BOOL)
            return TYPE_BOOL
        self._annotate(node, TYPE_ANY)
        return TYPE_ANY

    # ---- Literales ----

    def _visit_number(self, node: NumberNode) -> str:
        t = TYPE_REAL if isinstance(node.value, float) else TYPE_INT
        self._annotate(node, t)
        return t

    def _visit_string(self, node: StringNode) -> str:
        self._annotate(node, TYPE_STRING)
        return TYPE_STRING

    def _visit_bool(self, node: BoolNode) -> str:
        self._annotate(node, TYPE_BOOL)
        return TYPE_BOOL

    def _visit_variable(self, node: VariableNode) -> str:
        # Builtin como sqrt, sin, … tratados como variables en el parser
        if node.name in BUILTIN_TYPES:
            t = BUILTIN_TYPES[node.name]
            self._annotate(node, t)
            return t

        info = self.symbols.lookup_variable(node.name)
        if info is None:
            # --- SE001: variable no declarada ---
            self._error(
                "SE001",
                f"La variable '{node.name}' no está declarada antes de su uso.",
                node.line,
            )
            self._annotate(node, TYPE_ANY)
            return TYPE_ANY

        self._annotate(node, info.sym_type)
        return info.sym_type

    # ------------------------------------------------------------------ #
    #  Helpers                                                            #
    # ------------------------------------------------------------------ #

    def _annotate(self, node: Node, inferred_type: str) -> None:
        """Anota el tipo inferido en el nodo si el atributo existe."""
        try:
            object.__setattr__(node, "inferred_type", inferred_type)
        except (AttributeError, TypeError):
            pass  # Nodos que no tienen el slot; no es error crítico

    def _error(self, code: str, message: str, line: int) -> None:
        self.errors.append(SemanticError(code=code, message=message, line=line))


# ---------------------------------------------------------------------------
# Función de conveniencia
# ---------------------------------------------------------------------------

def analyze_semantics(program: ProgramNode) -> tuple[list[SemanticError], SymbolTable]:
    """Ejecuta el análisis semántico y devuelve (errores, tabla de símbolos)."""
    analyzer = SemanticAnalyzer()
    errors = analyzer.analyze(program)
    return errors, analyzer.symbols
