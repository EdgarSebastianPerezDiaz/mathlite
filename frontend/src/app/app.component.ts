import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs';
import { MathliteApiService } from './mathlite-api.service';
import {
  AnalyzeResponse,
  DiagnosticDto,
  RuntimeErrorDto,
  SemanticErrorDto,
  SymbolFuncDto,
  SymbolVarDto,
  TokenDto,
} from './models';

const EXAMPLE_SOURCE = `-- Programa de ejemplo MathLite
let base = 5
let altura = 3.0

def area(b, h) {
  return (b * h) / 2
}

let resultado = area(base, altura)
print(resultado)

-- Comparacion booleana
let esMayor = base > 2
if esMayor {
  print(resultado)
}
`;

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent {
  source = EXAMPLE_SOURCE;
  loading = false;
  response: AnalyzeResponse | null = null;
  transportError = '';

  /** Panel activo en la sección de resultados */
  activeTab: 'tokens' | 'output' | 'diagnostics' | 'semantic' | 'symbols' | 'ast' = 'tokens';

  constructor(private readonly api: MathliteApiService) {}

  analyze(): void {
    this.loading = true;
    this.transportError = '';
    this.api
      .analyze(this.source)
      .pipe(finalize(() => (this.loading = false)))
      .subscribe({
        next: (response) => {
          this.response = response;
          // Navegar a la pestaña más relevante según el resultado
          if (response.semantic_errors?.length) {
            this.activeTab = 'semantic';
          } else if (response.lexer_errors?.length || response.parser_errors?.length) {
            this.activeTab = 'diagnostics';
          } else {
            // Programa válido: mostrar la salida de la ejecución
            this.activeTab = 'output';
          }
        },
        error: (error) => {
          this.response = null;
          this.transportError = this.formatTransportError(error);
        },
      });
  }

  loadExample(): void {
    this.source = EXAMPLE_SOURCE;
  }

  clear(): void {
    this.source = '';
    this.response = null;
    this.transportError = '';
  }

  setTab(tab: 'tokens' | 'output' | 'diagnostics' | 'semantic' | 'symbols' | 'ast'): void {
    this.activeTab = tab;
  }

  // ── Getters ──────────────────────────────────────────────────────────────

  get tokens(): TokenDto[] {
    return this.response?.tokens ?? [];
  }

  get lexerParserErrors(): DiagnosticDto[] {
    return [
      ...(this.response?.lexer_errors ?? []),
      ...(this.response?.parser_errors ?? []),
    ];
  }

  get semanticErrors(): SemanticErrorDto[] {
    return this.response?.semantic_errors ?? [];
  }

  get symbolVars(): SymbolVarDto[] {
    return this.response?.symbol_table?.variables ?? [];
  }

  get symbolFuncs(): SymbolFuncDto[] {
    return this.response?.symbol_table?.functions ?? [];
  }

  get astText(): string {
    return this.response?.ast_text ?? '';
  }

  get output(): string[] {
    return this.response?.output ?? [];
  }

  get outputText(): string {
    return (this.response?.output ?? []).join('\n');
  }

  get runtimeErrors(): RuntimeErrorDto[] {
    return this.response?.runtime_errors ?? [];
  }

  get totalErrors(): number {
    return this.lexerParserErrors.length + this.semanticErrors.length;
  }

  get statusLabel(): string {
    if (!this.response) return 'Listo para analizar';
    if (this.loading) return 'Procesando…';
    if (this.response.ok) return 'Análisis completo';
    return `${this.totalErrors} error(es) detectado(s)`;
  }

  get statusSub(): string {
    if (!this.response) return 'El panel muestra el resultado de la última ejecución';
    if (this.response.ok) return 'Sin errores léxicos, sintácticos ni semánticos';
    const parts: string[] = [];
    if (this.lexerParserErrors.length) parts.push(`${this.lexerParserErrors.length} léxico/sintáctico`);
    if (this.semanticErrors.length) parts.push(`${this.semanticErrors.length} semántico`);
    return parts.join(' · ');
  }

  badgeColor(code: string): string {
    return '#334155'; /* Gris Slate sobrio y uniforme */
  }

  private formatTransportError(error: unknown): string {
    if (typeof error === 'object' && error && 'message' in error) {
      return String((error as { message?: unknown }).message ?? 'Error inesperado');
    }
    return 'No se pudo conectar con el servicio de análisis.';
  }
}