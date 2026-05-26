import urllib.request
import json

SOURCE_VALID = """\
-- Programa valido
let base = 5
let altura = 3.0

def area(b, h) {
  return (b * h) / 2
}

let resultado = area(base, altura)
print(resultado)
"""

SOURCE_ERRORS = """\
let x = 10
let x = 20
let r = "hola" + 5
return 99
print(noDeclarada)
"""

COLORS = {
    "SE001": "\033[38;5;214m",  # naranja
    "SE002": "\033[38;5;226m",  # amarillo
    "SE003": "\033[38;5;196m",  # rojo
    "SE004": "\033[38;5;141m",  # violeta
    "SE005": "\033[38;5;51m",   # cyan
    "SE006": "\033[38;5;213m",  # rosa
    "SE007": "\033[38;5;43m",   # teal
    "SE008": "\033[38;5;63m",   # indigo
}
RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
BOLD = "\033[1m"


def call(source: str) -> dict:
    body = json.dumps({"source": source}).encode()
    req = urllib.request.Request(
        "http://localhost:8000/api/analyze",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def separator(title: str) -> None:
    line = "─" * 62
    print(f"\n{BOLD}{line}")
    print(f"  {title}")
    print(f"{line}{RESET}")


# ── Test 1: Programa válido ──────────────────────────────────────────
separator("TEST 1: Programa válido (debe tener 0 errores semánticos)")
data = call(SOURCE_VALID)
ok = data["ok"]
sem_errors = data["semantic_errors"]
st = data["symbol_table"]

print(f"  ok       : {GREEN + 'True' + RESET if ok else RED + 'False' + RESET}")
print(f"  sem_errors: {len(sem_errors)}")
print(f"\n  {BOLD}Tabla de símbolos – Variables globales:{RESET}")
for v in st["variables"]:
    print(f"    {v['name']:12s}  tipo={BOLD}{v['type']}{RESET}  línea={v['line']}")
print(f"\n  {BOLD}Tabla de símbolos – Funciones:{RESET}")
for f in st["functions"]:
    print(f"    {f['name']:12s}  params={f['params']}  línea={f['line']}")

# ── Test 2: Programa con errores semánticos ──────────────────────────
separator("TEST 2: Programa con errores semánticos")
data2 = call(SOURCE_ERRORS)
ok2 = data2["ok"]
sem2 = data2["semantic_errors"]

print(f"  ok       : {GREEN + 'True' + RESET if ok2 else RED + 'False' + RESET}")
print(f"  sem_errors: {len(sem2)}\n")
for e in sem2:
    color = COLORS.get(e["code"], "")
    print(f"  {color}{BOLD}{e['code']}{RESET}  línea {e['line']:>2}  {e['message']}")

# ── Resumen de categorías detectadas ────────────────────────────────
separator("RESUMEN — Categorías de error detectadas")
codes = {e["code"] for e in sem2}
categories = {
    "SE001": "Variable no declarada",
    "SE002": "Redeclaración en mismo alcance",
    "SE003": "Función no definida",
    "SE004": "Aridad incorrecta",
    "SE005": "Tipo incompatible",
    "SE006": "Return fuera de función",
    "SE007": "Operador lógico sobre no-Bool",
    "SE008": "Condición no booleana",
}
for code, desc in categories.items():
    status = f"{GREEN}✓{RESET}" if code in codes else f"  "
    print(f"  {status} {COLORS.get(code,'')}{BOLD}{code}{RESET}  {desc}")
print()
