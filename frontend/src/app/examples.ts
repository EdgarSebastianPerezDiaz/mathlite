// Los 25 casos de prueba de MathLite, disponibles como ejemplos en la interfaz.
// El código coincide con la suite automatizada (tests/test_mathlite.py).

export interface Example {
  id: string;
  label: string;
  source: string;
}

export const EXAMPLES: Example[] = [
  // ── Programas válidos ──────────────────────────────────────────────
  {
    id: '01',
    label: '01 · Aritmética con precedencia',
    source: `let x = (3 + 4 * 2) / (1 - 5) ^ 2
print(x)`,
  },
  {
    id: '02',
    label: '02 · Factorial recursivo',
    source: `def factorial(n) {
  if n <= 1 { return 1 }
  return n * factorial(n - 1)
}
print(factorial(5))`,
  },
  {
    id: '03',
    label: '03 · While con acumulador',
    source: `let suma = 0
let i = 1
while i <= 10 {
  let suma = suma + i
  let i = i + 1
}
print(suma)`,
  },
  {
    id: '04',
    label: '04 · Funciones integradas (sqrt, abs)',
    source: `let y = sqrt(abs(-16.0))
print(y)`,
  },
  {
    id: '05',
    label: '05 · Función que llama a otra',
    source: `def cuadrado(x) { return x * x }
def hipotenusa(a, b) { return sqrt(cuadrado(a) + cuadrado(b)) }
print(hipotenusa(3, 4))`,
  },
  {
    id: '06',
    label: '06 · Condicional if/else',
    source: `let x = 7
if x > 5 { print(x) } else { print(0) }`,
  },
  {
    id: '07',
    label: '07 · Booleanos y lógicos',
    source: `let a = true
let b = false
if a and not b { print(1) }`,
  },
  {
    id: '08',
    label: '08 · Concatenación de cadenas',
    source: `let s = "hola" + "mundo"
print(s)`,
  },
  {
    id: '09',
    label: '09 · Módulo y potencia',
    source: `print(10 % 3)
print(2 ^ 5)`,
  },
  {
    id: '10',
    label: '10 · Promoción Int a Real',
    source: `let x = 5 + 2.0
print(x)`,
  },
  {
    id: '11',
    label: '11 · Builtins floor y ceil',
    source: `print(floor(3.7))
print(ceil(3.2))`,
  },
  {
    id: '12',
    label: '12 · Comentarios ignorados',
    source: `-- esto es un comentario
let x = 5  -- otro comentario
print(x)`,
  },
  // ── Errores léxicos ────────────────────────────────────────────────
  {
    id: '13',
    label: '13 · [Léxico] Carácter inválido',
    source: `let x = @5`,
  },
  {
    id: '14',
    label: '14 · [Léxico] Cadena sin cerrar',
    source: `let s = "hola`,
  },
  {
    id: '15',
    label: '15 · [Léxico] Error no aborta análisis',
    source: `let x = @
let y = 5`,
  },
  // ── Errores sintácticos ────────────────────────────────────────────
  {
    id: '16',
    label: '16 · [Sintáctico] Paréntesis sin cerrar',
    source: `let x = (3 + 4 * 2`,
  },
  {
    id: '17',
    label: '17 · [Sintáctico] Función sin bloque',
    source: `def f(x) return x`,
  },
  {
    id: '18',
    label: '18 · [Sintáctico] if sin condición',
    source: `if { print(1) }`,
  },
  // ── Errores semánticos ─────────────────────────────────────────────
  {
    id: '19',
    label: '19 · [SE001] Variable no declarada',
    source: `print(noDeclarada)`,
  },
  {
    id: '20',
    label: '20 · [SE002] Función duplicada',
    source: `def f(x) { return x }
def f(y) { return y }`,
  },
  {
    id: '21',
    label: '21 · [SE003] Función no definida',
    source: `print(noExiste(5))`,
  },
  {
    id: '22',
    label: '22 · [SE004] Aridad incorrecta',
    source: `def suma(a, b) { return a + b }
print(suma(1))`,
  },
  {
    id: '23',
    label: '23 · [SE005] Tipos incompatibles',
    source: `let x = "hola" + 5`,
  },
  {
    id: '24',
    label: '24 · [SE006] Return fuera de función',
    source: `return 99`,
  },
  // ── Error en tiempo de ejecución ───────────────────────────────────
  {
    id: '25',
    label: '25 · [RE001] División por cero',
    source: `let r = 10 / 0
print(r)`,
  },
];
