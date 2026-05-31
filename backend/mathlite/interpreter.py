"""mathlite.interpreter — Fase 5: Intérprete (evaluación del AST)
================================================================
Recorre el AST producido por el parser (Fase 3) y *ejecuta* el programa,
evaluando expresiones y ejecutando sentencias mediante el patrón Visitor.

Características
--------------
* Entorno de ejecución (diccionario de variables) separado por función.
* Paso de argumentos por valor en llamadas a funciones de usuario.
* Funciones matemáticas integradas: sin, cos, tan, sqrt, log, abs, floor, ceil.
* Precedencia y asociatividad ya resueltas por la estructura del AST.
* Errores en tiempo de ejecución (división por cero, función no definida,
  argumento inválido) reportados con número de línea, sin abortar con un
  traceback crudo de Python.
* Captura toda la salida de ``print`` para mostrarla en la interfaz web.

Semántica de variables
-----------------------
``let`` declara o reasigna en el alcance actual (coherente con los ejemplos
del informe, p. ej. ``let suma = suma + i`` dentro de un ``while``).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

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


# ---------------------------------------------------------------------------
# Errores en tiempo de ejecución
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class RuntimeErrorML:
    """Error detectado durante la interpretación.

    Categorías (campo ``code``):
      RE001 – división por cero
      RE002 – función no definida
      RE003 – argumento inválido para función integrada
      RE004 – variable no definida en ejecución
      RE005 – operación con tipos inválidos en ejecución
    """

    code: str
    message: str
    line: int


class MathLiteRuntimeError(Exception):
    """Excepción interna que transporta un RuntimeErrorML hasta el orquestador."""

    def __init__(self, code: str, message: str, line: int) -> None:
        super().__init__(message)
        self.error = RuntimeErrorML(code=code, message=message, line=line)


class ReturnSignal(Exception):
    """Señal de control para propagar un ``return`` fuera del cuerpo de función."""

    def __init__(self, value: Any) -> None:
        super().__init__()
        self.value = value


# ---------------------------------------------------------------------------
# Entorno de ejecución
# ---------------------------------------------------------------------------

@dataclass
class Environment:
    """Diccionario de variables de un alcance (global o de una función)."""

    values: dict[str, Any] = field(default_factory=dict)

    def define(self, name: str, value: Any) -> None:
        self.values[name] = value

    def get(self, name: str) -> Any:
        return self.values[name]

    def has(self, name: str) -> bool:
        return name in self.values


# Funciones matemáticas integradas: nombre -> (callable, n.º de argumentos)
BUILTINS: dict[str, tuple] = {
    "sin": (math.sin, 1),
    "cos": (math.cos, 1),
    "tan": (math.tan, 1),
    "sqrt": (math.sqrt, 1),
    "log": (math.log, 1),
    "abs": (abs, 1),
    "floor": (math.floor, 1),
    "ceil": (math.ceil, 1),
}


# ---------------------------------------------------------------------------
# Intérprete
# ---------------------------------------------------------------------------

class Interpreter:
    """Evalúa un ProgramNode recorriendo el AST (patrón Visitor)."""

    def __init__(self) -> None:
        self.global_env = Environment()
        self.functions: dict[str, FuncDefNode] = {}
        self.output: list[str] = []   # líneas capturadas de print
        self.errors: list[RuntimeErrorML] = []

    # ------------------------------------------------------------------ #
    #  Punto de entrada                                                    #
    # ------------------------------------------------------------------ #

    def interpret(self, program: ProgramNode) -> dict:
        """Ejecuta el programa y devuelve salida + errores en tiempo de ejecución."""
        self.global_env = Environment()
        self.functions = {}
        self.output = []
        self.errors = []

        # Primer pase: registrar todas las funciones (permite llamadas hacia adelante)
        for stmt in program.statements:
            if isinstance(stmt, FuncDefNode):
                self.functions[stmt.name] = stmt

        # Segundo pase: ejecutar las sentencias de nivel superior
        try:
            for stmt in program.statements:
                if not isinstance(stmt, FuncDefNode):
                    self._execute(stmt, self.global_env)
        except MathLiteRuntimeError as exc:
            self.errors.append(exc.error)
        except ReturnSignal:
            pass  # return en el nivel superior: ignorado (ya es SE006 en semántico)

        return {
            "output": self.output,
            "runtime_errors": [
                {"code": e.code, "message": e.message, "line": e.line}
                for e in self.errors
            ],
        }

    # ------------------------------------------------------------------ #
    #  Modo REPL (evaluación línea a línea conservando estado)            #
    # ------------------------------------------------------------------ #

    def eval_line(self, program: ProgramNode) -> dict:
        """Ejecuta las sentencias de UNA entrada del REPL SIN reiniciar el estado.

        A diferencia de ``interpret``, conserva ``global_env`` y ``functions``
        entre llamadas, de modo que el usuario puede declarar una variable en
        una línea y usarla en la siguiente. Devuelve la salida producida por
        esa entrada y, si la última sentencia fue una expresión, su valor.
        """
        self.output = []
        self.errors = []
        result_value: Any = None

        # Registrar funciones definidas en esta entrada
        for stmt in program.statements:
            if isinstance(stmt, FuncDefNode):
                self.functions[stmt.name] = stmt

        try:
            for stmt in program.statements:
                if isinstance(stmt, FuncDefNode):
                    continue
                if isinstance(stmt, ExpressionStmtNode):
                    # En el REPL, una expresión suelta devuelve su valor
                    result_value = self._evaluate(stmt.expression, self.global_env)
                else:
                    self._execute(stmt, self.global_env)
        except MathLiteRuntimeError as exc:
            self.errors.append(exc.error)
        except ReturnSignal:
            pass

        return {
            "output": self.output,
            "result": None if result_value is None else self._stringify(result_value),
            "runtime_errors": [
                {"code": e.code, "message": e.message, "line": e.line}
                for e in self.errors
            ],
        }

    # ------------------------------------------------------------------ #
    #  Ejecución de sentencias                                            #
    # ------------------------------------------------------------------ #

    def _execute(self, node: Node | None, env: Environment) -> None:
        if node is None:
            return
        if isinstance(node, AssignNode):
            self._exec_assign(node, env)
        elif isinstance(node, PrintNode):
            self._exec_print(node, env)
        elif isinstance(node, IfNode):
            self._exec_if(node, env)
        elif isinstance(node, WhileNode):
            self._exec_while(node, env)
        elif isinstance(node, ReturnNode):
            self._exec_return(node, env)
        elif isinstance(node, BlockNode):
            self._exec_block(node, env)
        elif isinstance(node, FuncDefNode):
            self.functions[node.name] = node
        elif isinstance(node, ExpressionStmtNode):
            self._evaluate(node.expression, env)
        else:
            # Cualquier otra cosa a nivel de sentencia: evaluarla como expresión
            self._evaluate(node, env)

    def _exec_assign(self, node: AssignNode, env: Environment) -> None:
        value = self._evaluate(node.value, env)
        env.define(node.name, value)   # let: declara o reasigna en el alcance actual

    def _exec_print(self, node: PrintNode, env: Environment) -> None:
        value = self._evaluate(node.value, env)
        self.output.append(self._stringify(value))

    def _exec_if(self, node: IfNode, env: Environment) -> None:
        if self._is_truthy(self._evaluate(node.condition, env)):
            self._exec_block(node.then_branch, env)
        elif node.else_branch is not None:
            self._exec_block(node.else_branch, env)

    def _exec_while(self, node: WhileNode, env: Environment) -> None:
        guard = 0
        while self._is_truthy(self._evaluate(node.condition, env)):
            self._exec_block(node.body, env)
            guard += 1
            if guard > 1_000_000:   # red de seguridad anti bucle infinito
                raise MathLiteRuntimeError(
                    "RE006",
                    "El ciclo 'while' superó el límite de iteraciones permitido.",
                    node.line,
                )

    def _exec_return(self, node: ReturnNode, env: Environment) -> None:
        value = self._evaluate(node.value, env) if node.value is not None else None
        raise ReturnSignal(value)

    def _exec_block(self, node: BlockNode | None, env: Environment) -> None:
        if node is None:
            return
        for stmt in node.statements:
            self._execute(stmt, env)

    # ------------------------------------------------------------------ #
    #  Evaluación de expresiones                                          #
    # ------------------------------------------------------------------ #

    def _evaluate(self, node: Node | None, env: Environment) -> Any:
        if node is None:
            return None
        if isinstance(node, NumberNode):
            return node.value
        if isinstance(node, StringNode):
            return node.value
        if isinstance(node, BoolNode):
            return node.value
        if isinstance(node, VariableNode):
            return self._eval_variable(node, env)
        if isinstance(node, UnaryOpNode):
            return self._eval_unary(node, env)
        if isinstance(node, BinOpNode):
            return self._eval_binop(node, env)
        if isinstance(node, FuncCallNode):
            return self._eval_call(node, env)
        raise MathLiteRuntimeError(
            "RE005",
            f"No se puede evaluar el nodo {node.__class__.__name__}.",
            getattr(node, "line", 0),
        )

    def _eval_variable(self, node: VariableNode, env: Environment) -> Any:
        if env.has(node.name):
            return env.get(node.name)
        if self.global_env.has(node.name):
            return self.global_env.get(node.name)
        raise MathLiteRuntimeError(
            "RE004",
            f"La variable '{node.name}' no tiene valor en tiempo de ejecución.",
            node.line,
        )

    def _eval_unary(self, node: UnaryOpNode, env: Environment) -> Any:
        operand = self._evaluate(node.operand, env)
        if node.op == "-":
            return -operand
        if node.op == "not":
            return not self._is_truthy(operand)
        raise MathLiteRuntimeError(
            "RE005", f"Operador unario desconocido '{node.op}'.", node.line
        )

    def _eval_binop(self, node: BinOpNode, env: Environment) -> Any:
        op = node.op

        # Cortocircuito lógico
        if op == "and":
            left = self._evaluate(node.left, env)
            if not self._is_truthy(left):
                return False
            return self._is_truthy(self._evaluate(node.right, env))
        if op == "or":
            left = self._evaluate(node.left, env)
            if self._is_truthy(left):
                return True
            return self._is_truthy(self._evaluate(node.right, env))

        left = self._evaluate(node.left, env)
        right = self._evaluate(node.right, env)

        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                raise MathLiteRuntimeError(
                    "RE001", "División por cero.", node.line
                )
            result = left / right
            # Mantener Int si ambos son enteros y la división es exacta
            if isinstance(left, int) and isinstance(right, int) and left % right == 0:
                return left // right
            return result
        if op == "%":
            if right == 0:
                raise MathLiteRuntimeError(
                    "RE001", "Módulo por cero.", node.line
                )
            return left % right
        if op == "^":
            return left ** right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == "<":
            return left < right
        if op == ">":
            return left > right
        if op == "<=":
            return left <= right
        if op == ">=":
            return left >= right

        raise MathLiteRuntimeError(
            "RE005", f"Operador binario desconocido '{op}'.", node.line
        )

    def _eval_call(self, node: FuncCallNode, env: Environment) -> Any:
        args = [self._evaluate(arg, env) for arg in node.args]

        # 1. Funciones integradas
        if node.callee in BUILTINS:
            func, arity = BUILTINS[node.callee]
            if len(args) != arity:
                raise MathLiteRuntimeError(
                    "RE003",
                    f"La función '{node.callee}' espera {arity} argumento(s), "
                    f"se recibieron {len(args)}.",
                    node.line,
                )
            try:
                return func(*args)
            except (ValueError, TypeError) as exc:
                raise MathLiteRuntimeError(
                    "RE003",
                    f"Argumento inválido para '{node.callee}': {exc}.",
                    node.line,
                )

        # 2. Funciones definidas por el usuario
        func_def = self.functions.get(node.callee)
        if func_def is None:
            raise MathLiteRuntimeError(
                "RE002",
                f"La función '{node.callee}' no está definida.",
                node.line,
            )

        if len(args) != len(func_def.params):
            raise MathLiteRuntimeError(
                "RE003",
                f"La función '{node.callee}' espera {len(func_def.params)} "
                f"argumento(s), se recibieron {len(args)}.",
                node.line,
            )

        # Nuevo entorno local; paso de argumentos por valor
        local_env = Environment()
        for param, value in zip(func_def.params, args):
            local_env.define(param, value)

        try:
            self._exec_block(func_def.body, local_env)
        except ReturnSignal as signal:
            return signal.value
        return None   # función sin return explícito

    # ------------------------------------------------------------------ #
    #  Helpers                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _is_truthy(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        return True

    @staticmethod
    def _stringify(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if value is None:
            return "void"
        if isinstance(value, float) and value.is_integer():
            # 7.0 -> "7.0" para dejar claro que es Real
            return f"{value:.1f}"
        return str(value)


# ---------------------------------------------------------------------------
# Función de conveniencia
# ---------------------------------------------------------------------------

def interpret_program(program: ProgramNode) -> dict:
    """Ejecuta el programa y devuelve {'output': [...], 'runtime_errors': [...]}"""
    interpreter = Interpreter()
    return interpreter.interpret(program)


def repl() -> None:
    """Modo interactivo de consola (lee-evalúa-imprime) que conserva estado.

    Cada línea se tokeniza, parsea e interpreta sin reiniciar el entorno, de
    modo que las variables y funciones declaradas persisten entre entradas.
    Escribe 'salir' o 'exit' (o Ctrl-D) para terminar.
    """
    from .lexer import Lexer
    from .parser import Parser

    interpreter = Interpreter()
    print("MathLite REPL — escribe 'salir' para terminar.")
    while True:
        try:
            line = input(">>> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.strip() in {"salir", "exit"}:
            break
        if not line.strip():
            continue

        tokens, lex_errors = Lexer(line).scan_tokens()
        if lex_errors:
            for e in lex_errors:
                print(f"  Error léxico L{e.line}:C{e.column} — {e.message}")
            continue

        parser = Parser(tokens)
        program = parser.parse()
        if parser.errors:
            for e in parser.errors:
                print(f"  Error sintáctico L{e.line} — {e.message}")
            continue

        result = interpreter.eval_line(program)
        for out in result["output"]:
            print(out)
        for e in result["runtime_errors"]:
            print(f"  {e['code']} L{e['line']} — {e['message']}")
        if result["result"] is not None:
            print(f"= {result['result']}")


if __name__ == "__main__":
    repl()