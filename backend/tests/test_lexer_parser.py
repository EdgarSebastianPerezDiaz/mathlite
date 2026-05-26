from mathlite.lexer import Lexer, TokenType
from mathlite.parser import Parser, ast_to_text


def test_lexer_recognizes_basic_program() -> None:
    source = "let x = 3 + 4 * 2\nprint(x)\n"
    tokens, errors = Lexer(source).scan_tokens()
    assert not errors
    assert [token.type for token in tokens[:8]] == [
        TokenType.LET,
        TokenType.IDENT,
        TokenType.ASSIGN,
        TokenType.ENTERO,
        TokenType.PLUS,
        TokenType.ENTERO,
        TokenType.STAR,
        TokenType.ENTERO,
    ]


def test_parser_builds_ast_for_assignment_and_print() -> None:
    source = "let x = 3 + 4 * 2\nprint(x)\n"
    tokens, _ = Lexer(source).scan_tokens()
    parser = Parser(tokens)
    program = parser.parse()
    text = ast_to_text(program)
    assert "Program" in text
    assert "Assign(x)" in text
    assert "Print" in text
