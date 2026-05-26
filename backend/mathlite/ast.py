from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Node:
    line: int
    inferred_type: str = ""   # anotado por el analizador semántico (Fase 4)


@dataclass(slots=True)
class ProgramNode(Node):
    statements: list[Node] = field(default_factory=list)


@dataclass(slots=True)
class BlockNode(Node):
    statements: list[Node] = field(default_factory=list)


@dataclass(slots=True)
class NumberNode(Node):
    value: Any = 0


@dataclass(slots=True)
class StringNode(Node):
    value: str = ""


@dataclass(slots=True)
class BoolNode(Node):
    value: bool = False


@dataclass(slots=True)
class VariableNode(Node):
    name: str = ""


@dataclass(slots=True)
class UnaryOpNode(Node):
    op: str = ""
    operand: Node | None = None


@dataclass(slots=True)
class BinOpNode(Node):
    left: Node | None = None
    op: str = ""
    right: Node | None = None


@dataclass(slots=True)
class AssignNode(Node):
    name: str = ""
    value: Node | None = None


@dataclass(slots=True)
class FuncDefNode(Node):
    name: str = ""
    params: list[str] = field(default_factory=list)
    body: BlockNode | None = None


@dataclass(slots=True)
class FuncCallNode(Node):
    callee: str = ""
    args: list[Node] = field(default_factory=list)


@dataclass(slots=True)
class IfNode(Node):
    condition: Node | None = None
    then_branch: BlockNode | None = None
    else_branch: BlockNode | None = None


@dataclass(slots=True)
class WhileNode(Node):
    condition: Node | None = None
    body: BlockNode | None = None


@dataclass(slots=True)
class PrintNode(Node):
    value: Node | None = None


@dataclass(slots=True)
class ReturnNode(Node):
    value: Node | None = None


@dataclass(slots=True)
class ExpressionStmtNode(Node):
    expression: Node | None = None

