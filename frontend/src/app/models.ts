export interface TokenDto {
  type: string;
  lexeme: string;
  line: number;
  column: number;
  literal: unknown;
}

export interface DiagnosticDto {
  message: string;
  line: number;
  column: number;
}

export interface SemanticErrorDto {
  code: string;
  message: string;
  line: number;
}

export interface RuntimeErrorDto {
  code: string;
  message: string;
  line: number;
}

export interface SymbolVarDto {
  name: string;
  type: string;
  line: number;
}

export interface SymbolFuncDto {
  name: string;
  params: string[];
  line: number;
}

export interface SymbolTableDto {
  variables: SymbolVarDto[];
  functions: SymbolFuncDto[];
}

export interface AnalyzeResponse {
  tokens: TokenDto[];
  lexer_errors: DiagnosticDto[];
  parser_errors: DiagnosticDto[];
  semantic_errors: SemanticErrorDto[];
  ast: unknown;
  ast_text: string;
  symbol_table: SymbolTableDto;
  output: string[];
  runtime_errors: RuntimeErrorDto[];
  ok: boolean;
}