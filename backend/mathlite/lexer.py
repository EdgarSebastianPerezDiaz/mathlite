from __future__ import annotations

from dataclasses import dataclass

from .errors import LexError


class TokenType:
    ENTERO = "ENTERO"
    REAL = "REAL"
    STRING = "STRING"
    BOOL = "BOOL"
    IDENT = "IDENT"
    BUILTIN = "BUILTIN"
    LET = "LET"
    DEF = "DEF"
    RETURN = "RETURN"
    IF = "IF"
    ELSE = "ELSE"
    WHILE = "WHILE"
    PRINT = "PRINT"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    PLUS = "PLUS"
    MINUS = "MINUS"
    STAR = "STAR"
    SLASH = "SLASH"
    CARET = "CARET"
    PERCENT = "PERCENT"
    ASSIGN = "ASSIGN"
    EQ = "EQ"
    NEQ = "NEQ"
    LT = "LT"
    GT = "GT"
    LTE = "LTE"
    GTE = "GTE"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    COMMA = "COMMA"
    SEMICOLON = "SEMICOLON"
    NEWLINE = "NEWLINE"
    EOF = "EOF"


@dataclass(slots=True)
class Token:
    type: str
    lexeme: str
    line: int
    column: int
    literal: object | None = None


KEYWORDS = {
    "let": TokenType.LET,
    "def": TokenType.DEF,
    "return": TokenType.RETURN,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "print": TokenType.PRINT,
    "true": TokenType.BOOL,
    "false": TokenType.BOOL,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
}

BUILTINS = {"sin", "cos", "tan", "sqrt", "log", "abs", "floor", "ceil"}


class Lexer:
    def __init__(self, source: str) -> None:
        self.source = source
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []
        self.errors: list[LexError] = []

    def scan_tokens(self) -> tuple[list[Token], list[LexError]]:
        while not self._is_at_end():
            self.start = self.current
            self.start_column = self.column
            self._scan_token()
        self.tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return self.tokens, self.errors

    def _scan_token(self) -> None:
        c = self._advance()
        if c in " \r\t":
            return
        if c == "\n":
            self.tokens.append(Token(TokenType.NEWLINE, "\n", self.line - 1, 0))
            return
        if c == ";":
            self.tokens.append(Token(TokenType.SEMICOLON, c, self.line, self.start_column))
            return
        if c == "(":
            self._add(TokenType.LPAREN)
            return
        if c == ")":
            self._add(TokenType.RPAREN)
            return
        if c == "{":
            self._add(TokenType.LBRACE)
            return
        if c == "}":
            self._add(TokenType.RBRACE)
            return
        if c == ",":
            self._add(TokenType.COMMA)
            return
        if c == "+":
            self._add(TokenType.PLUS)
            return
        if c == "-":
            if self._match("-"):
                self._skip_comment()
            else:
                self._add(TokenType.MINUS)
            return
        if c == "*":
            self._add(TokenType.STAR)
            return
        if c == "/":
            self._add(TokenType.SLASH)
            return
        if c == "^":
            self._add(TokenType.CARET)
            return
        if c == "%":
            self._add(TokenType.PERCENT)
            return
        if c == "=":
            self._add(TokenType.EQ if self._match("=") else TokenType.ASSIGN)
            return
        if c == "!":
            if self._match("="):
                self._add(TokenType.NEQ)
            else:
                self._lex_error("caracter invalido '!' ")
            return
        if c == "<":
            self._add(TokenType.LTE if self._match("=") else TokenType.LT)
            return
        if c == ">":
            self._add(TokenType.GTE if self._match("=") else TokenType.GT)
            return
        if c == '"':
            self._string()
            return
        if c.isdigit():
            self._number()
            return
        if c.isalpha() or c == "_":
            self._identifier()
            return
        self._lex_error(f"caracter invalido '{c}'")

    def _identifier(self) -> None:
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()
        lexeme = self.source[self.start:self.current]
        token_type = KEYWORDS.get(lexeme)
        if token_type == TokenType.BOOL:
            self.tokens.append(Token(TokenType.BOOL, lexeme, self.line, self.start_column, lexeme == "true"))
            return
        if token_type:
            self.tokens.append(Token(token_type, lexeme, self.line, self.start_column))
            return
        if lexeme in BUILTINS:
            self.tokens.append(Token(TokenType.BUILTIN, lexeme, self.line, self.start_column))
            return
        self.tokens.append(Token(TokenType.IDENT, lexeme, self.line, self.start_column))

    def _number(self) -> None:
        while self._peek().isdigit():
            self._advance()
        is_real = False
        if self._peek() == "." and self._peek_next().isdigit():
            is_real = True
            self._advance()
            while self._peek().isdigit():
                self._advance()
        lexeme = self.source[self.start:self.current]
        token_type = TokenType.REAL if is_real else TokenType.ENTERO
        value = float(lexeme) if is_real else int(lexeme)
        self.tokens.append(Token(token_type, lexeme, self.line, self.start_column, value))

    def _string(self) -> None:
        value = []
        while not self._is_at_end() and self._peek() != '"':
            if self._peek() == "\n":
                self._lex_error("cadena sin cerrar")
                return
            value.append(self._advance())
        if self._is_at_end():
            self._lex_error("cadena sin cerrar")
            return
        self._advance()
        lexeme = self.source[self.start:self.current]
        self.tokens.append(Token(TokenType.STRING, lexeme, self.line, self.start_column, "".join(value)))

    def _skip_comment(self) -> None:
        while not self._is_at_end() and self._peek() != "\n":
            self._advance()

    def _add(self, token_type: str) -> None:
        lexeme = self.source[self.start:self.current]
        self.tokens.append(Token(token_type, lexeme, self.line, self.start_column))

    def _lex_error(self, message: str) -> None:
        self.errors.append(LexError(message, self.line, self.start_column))

    def _advance(self) -> str:
        ch = self.source[self.current]
        self.current += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _match(self, expected: str) -> bool:
        if self._is_at_end() or self.source[self.current] != expected:
            return False
        self.current += 1
        self.column += 1
        return True

    def _peek(self) -> str:
        if self._is_at_end():
            return "\0"
        return self.source[self.current]

    def _peek_next(self) -> str:
        if self.current + 1 >= len(self.source):
            return "\0"
        return self.source[self.current + 1]

    def _is_at_end(self) -> bool:
        return self.current >= len(self.source)

