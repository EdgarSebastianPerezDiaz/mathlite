from __future__ import annotations

from dataclasses import asdict, is_dataclass

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
from .errors import ParseError
from .lexer import Token, TokenType


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.current = 0
        self.errors: list[ParseError] = []

    def parse(self) -> ProgramNode:
        statements: list[Node] = []
        self._skip_separators()
        while not self._is_at_end():
            try:
                statement = self._statement()
                if statement is not None:
                    statements.append(statement)
            except ParseError as error:
                self.errors.append(error)
                self._synchronize()
            self._skip_separators()
        return ProgramNode(line=1, statements=statements)

    def _statement(self) -> Node | None:
        if self._match(TokenType.LET):
            return self._declaration()
        if self._match(TokenType.DEF):
            return self._function_definition()
        if self._match(TokenType.IF):
            return self._if_statement()
        if self._match(TokenType.WHILE):
            return self._while_statement()
        if self._match(TokenType.PRINT):
            return self._print_statement()
        if self._match(TokenType.RETURN):
            return self._return_statement()
        return self._expression_statement()

    def _declaration(self) -> AssignNode:
        name = self._consume(TokenType.IDENT, "se esperaba un identificador despues de let")
        self._consume(TokenType.ASSIGN, "se esperaba '=' en la declaracion")
        value = self._expression()
        return AssignNode(line=name.line, name=name.lexeme, value=value)

    def _function_definition(self) -> FuncDefNode:
        name = self._consume(TokenType.IDENT, "se esperaba un nombre de funcion")
        self._consume(TokenType.LPAREN, "se esperaba '(' despues del nombre de funcion")
        params: list[str] = []
        if not self._check(TokenType.RPAREN):
            while True:
                param = self._consume(TokenType.IDENT, "se esperaba un parametro")
                params.append(param.lexeme)
                if not self._match(TokenType.COMMA):
                    break
        self._consume(TokenType.RPAREN, "se esperaba ')' al cerrar parametros")
        body = self._block()
        return FuncDefNode(line=name.line, name=name.lexeme, params=params, body=body)

    def _if_statement(self) -> IfNode:
        keyword = self._previous()
        condition = self._expression()
        then_branch = self._block()
        else_branch = None
        if self._match(TokenType.ELSE):
            else_branch = self._block()
        return IfNode(line=keyword.line, condition=condition, then_branch=then_branch, else_branch=else_branch)

    def _while_statement(self) -> WhileNode:
        keyword = self._previous()
        condition = self._expression()
        body = self._block()
        return WhileNode(line=keyword.line, condition=condition, body=body)

    def _print_statement(self) -> PrintNode:
        keyword = self._previous()
        self._consume(TokenType.LPAREN, "se esperaba '(' despues de print")
        value = self._expression()
        self._consume(TokenType.RPAREN, "se esperaba ')' despues de la expresion de print")
        return PrintNode(line=keyword.line, value=value)

    def _return_statement(self) -> ReturnNode:
        keyword = self._previous()
        value = self._expression()
        return ReturnNode(line=keyword.line, value=value)

    def _expression_statement(self) -> ExpressionStmtNode:
        expr = self._expression()
        return ExpressionStmtNode(line=expr.line, expression=expr)

    def _block(self) -> BlockNode:
        left_brace = self._consume(TokenType.LBRACE, "se esperaba '{' para abrir un bloque")
        statements: list[Node] = []
        self._skip_separators()
        while not self._check(TokenType.RBRACE) and not self._check(TokenType.EOF):
            try:
                statement = self._statement()
                if statement is not None:
                    statements.append(statement)
            except ParseError as error:
                self.errors.append(error)
                self._synchronize(stop_at_block_end=True)
            self._skip_separators()
        self._consume(TokenType.RBRACE, "se esperaba '}' para cerrar el bloque")
        return BlockNode(line=left_brace.line, statements=statements)

    def _expression(self) -> Node:
        return self._or()

    def _or(self) -> Node:
        expr = self._and()
        while self._match(TokenType.OR):
            op = self._previous()
            right = self._and()
            expr = BinOpNode(line=op.line, left=expr, op=op.lexeme, right=right)
        return expr

    def _and(self) -> Node:
        expr = self._not()
        while self._match(TokenType.AND):
            op = self._previous()
            right = self._not()
            expr = BinOpNode(line=op.line, left=expr, op=op.lexeme, right=right)
        return expr

    def _not(self) -> Node:
        if self._match(TokenType.NOT):
            op = self._previous()
            operand = self._not()
            return UnaryOpNode(line=op.line, op=op.lexeme, operand=operand)
        return self._comparison()

    def _comparison(self) -> Node:
        expr = self._term()
        while self._match(TokenType.EQ, TokenType.NEQ, TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            op = self._previous()
            right = self._term()
            expr = BinOpNode(line=op.line, left=expr, op=op.lexeme, right=right)
        return expr

    def _term(self) -> Node:
        expr = self._factor()
        while self._match(TokenType.PLUS, TokenType.MINUS):
            op = self._previous()
            right = self._factor()
            expr = BinOpNode(line=op.line, left=expr, op=op.lexeme, right=right)
        return expr

    def _factor(self) -> Node:
        expr = self._power()
        while self._match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self._previous()
            right = self._power()
            expr = BinOpNode(line=op.line, left=expr, op=op.lexeme, right=right)
        return expr

    def _power(self) -> Node:
        expr = self._unary()
        if self._match(TokenType.CARET):
            op = self._previous()
            right = self._power()
            expr = BinOpNode(line=op.line, left=expr, op=op.lexeme, right=right)
        return expr

    def _unary(self) -> Node:
        if self._match(TokenType.MINUS):
            op = self._previous()
            operand = self._unary()
            return UnaryOpNode(line=op.line, op=op.lexeme, operand=operand)
        return self._call()

    def _call(self) -> Node:
        expr = self._primary()
        while self._match(TokenType.LPAREN):
            paren = self._previous()
            arguments: list[Node] = []
            if not self._check(TokenType.RPAREN):
                while True:
                    arguments.append(self._expression())
                    if not self._match(TokenType.COMMA):
                        break
            self._consume(TokenType.RPAREN, "se esperaba ')' en la llamada a funcion")
            if isinstance(expr, VariableNode):
                expr = FuncCallNode(line=paren.line, callee=expr.name, args=arguments)
            else:
                raise self._error(paren, "solo se puede llamar a un identificador o funcion integrada")
        return expr

    def _primary(self) -> Node:
        if self._match(TokenType.BOOL):
            previous = self._previous()
            return BoolNode(line=previous.line, value=bool(previous.literal))
        if self._match(TokenType.ENTERO, TokenType.REAL):
            previous = self._previous()
            return NumberNode(line=previous.line, value=previous.literal)
        if self._match(TokenType.STRING):
            previous = self._previous()
            return StringNode(line=previous.line, value=str(previous.literal))
        if self._match(TokenType.IDENT, TokenType.BUILTIN):
            previous = self._previous()
            return VariableNode(line=previous.line, name=previous.lexeme)
        if self._match(TokenType.LPAREN):
            expr = self._expression()
            self._consume(TokenType.RPAREN, "se esperaba ')' despues de la expresion")
            return expr
        raise self._error(self._peek(), "token inesperado en una expresion")

    def _skip_separators(self) -> None:
        while self._match(TokenType.NEWLINE, TokenType.SEMICOLON):
            pass

    def _synchronize(self, stop_at_block_end: bool = False) -> None:
        while not self._is_at_end():
            if stop_at_block_end and self._check(TokenType.RBRACE):
                return
            if self._previous().type in {TokenType.NEWLINE, TokenType.SEMICOLON}:
                return
            if self._peek().type in {TokenType.LET, TokenType.DEF, TokenType.IF, TokenType.WHILE, TokenType.PRINT, TokenType.RETURN}:
                return
            self._advance()

    def _match(self, *types: str) -> bool:
        for token_type in types:
            if self._check(token_type):
                self._advance()
                return True
        return False

    def _consume(self, token_type: str, message: str) -> Token:
        if self._check(token_type):
            return self._advance()
        raise self._error(self._peek(), message)

    def _error(self, token: Token, message: str) -> ParseError:
        return ParseError(message=message, line=token.line, column=token.column)

    def _check(self, token_type: str) -> bool:
        if self._is_at_end():
            return token_type == TokenType.EOF
        return self._peek().type == token_type

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.current += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        return self._peek().type == TokenType.EOF

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]


def node_to_dict(node: Node | None) -> dict | None:
    if node is None:
        return None
    if is_dataclass(node):
        data = asdict(node)
        data["kind"] = node.__class__.__name__
        return data
    return {"kind": node.__class__.__name__}


def ast_to_text(node: Node | None) -> str:
    lines: list[str] = []

    def walk(current: Node | None, indent: str) -> None:
        if current is None:
            lines.append(f"{indent}None")
            return
        lines.append(f"{indent}{_label(current)}")
        child_indent = indent + "  "
        if isinstance(current, ProgramNode):
            for statement in current.statements:
                walk(statement, child_indent)
        elif isinstance(current, BlockNode):
            for statement in current.statements:
                walk(statement, child_indent)
        elif isinstance(current, AssignNode):
            walk(current.value, child_indent)
        elif isinstance(current, FuncDefNode):
            for param in current.params:
                lines.append(f"{child_indent}Param({param})")
            walk(current.body, child_indent)
        elif isinstance(current, FuncCallNode):
            for argument in current.args:
                walk(argument, child_indent)
        elif isinstance(current, IfNode):
            walk(current.condition, child_indent)
            walk(current.then_branch, child_indent)
            if current.else_branch is not None:
                walk(current.else_branch, child_indent)
        elif isinstance(current, WhileNode):
            walk(current.condition, child_indent)
            walk(current.body, child_indent)
        elif isinstance(current, PrintNode):
            walk(current.value, child_indent)
        elif isinstance(current, ReturnNode):
            walk(current.value, child_indent)
        elif isinstance(current, ExpressionStmtNode):
            walk(current.expression, child_indent)
        elif isinstance(current, UnaryOpNode):
            walk(current.operand, child_indent)
        elif isinstance(current, BinOpNode):
            walk(current.left, child_indent)
            walk(current.right, child_indent)

    walk(node, "")
    return "\n".join(lines)


def _label(node: Node) -> str:
    if isinstance(node, ProgramNode):
        return "Program"
    if isinstance(node, BlockNode):
        return "Block"
    if isinstance(node, NumberNode):
        return f"Number({node.value})"
    if isinstance(node, StringNode):
        return f'String("{node.value}")'
    if isinstance(node, BoolNode):
        return f"Bool({str(node.value).lower()})"
    if isinstance(node, VariableNode):
        return f"Variable({node.name})"
    if isinstance(node, UnaryOpNode):
        return f"Unary({node.op})"
    if isinstance(node, BinOpNode):
        return f"BinOp({node.op})"
    if isinstance(node, AssignNode):
        return f"Assign({node.name})"
    if isinstance(node, FuncDefNode):
        return f"FuncDef({node.name})"
    if isinstance(node, FuncCallNode):
        return f"Call({node.callee})"
    if isinstance(node, IfNode):
        return "If"
    if isinstance(node, WhileNode):
        return "While"
    if isinstance(node, PrintNode):
        return "Print"
    if isinstance(node, ReturnNode):
        return "Return"
    if isinstance(node, ExpressionStmtNode):
        return "ExprStmt"
    return node.__class__.__name__