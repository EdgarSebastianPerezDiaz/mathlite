from __future__ import annotations

from dataclasses import asdict

from .lexer import Lexer, Token
from .parser import Parser, ast_to_text, node_to_dict
from .semantic import analyze_semantics


def analyze_source(source: str) -> dict:
    # ── Fase 1: Análisis léxico ──────────────────────────────────────────
    lexer = Lexer(source)
    tokens, lexer_errors = lexer.scan_tokens()

    # ── Fase 2/3: Análisis sintáctico ────────────────────────────────────
    parser = Parser(tokens)
    program = parser.parse()

    # ── Fase 4: Análisis semántico ────────────────────────────────────────
    semantic_errors, symbol_table = analyze_semantics(program)

    # ── Serializar tabla de símbolos (solo globales para el cliente) ──────
    global_vars = [
        {
            "name": info.name,
            "type": info.sym_type,
            "line": info.line,
        }
        for info in symbol_table._globals.values()
    ]
    functions = [
        {
            "name": info.name,
            "params": info.param_names,
            "line": info.line,
        }
        for info in symbol_table._functions.values()
    ]

    ok = not lexer_errors and not parser.errors and not semantic_errors

    return {
        "tokens": [token_to_dict(token) for token in tokens if token.type != "EOF"],
        "lexer_errors": [asdict(error) for error in lexer_errors],
        "parser_errors": [asdict(error) for error in parser.errors],
        "semantic_errors": [asdict(error) for error in semantic_errors],
        "ast": node_to_dict(program),
        "ast_text": ast_to_text(program),
        "symbol_table": {
            "variables": global_vars,
            "functions": functions,
        },
        "ok": ok,
    }


def token_to_dict(token: Token) -> dict:
    return {
        "type": token.type,
        "lexeme": token.lexeme,
        "line": token.line,
        "column": token.column,
        "literal": token.literal,
    }
