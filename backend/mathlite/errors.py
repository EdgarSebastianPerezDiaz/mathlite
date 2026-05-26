from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class LexError:
    message: str
    line: int
    column: int


@dataclass(slots=True)
class ParseError:
    message: str
    line: int
    column: int


@dataclass(slots=True)
class SemanticError:
    """Error detectado durante el análisis semántico.

    Categorías (campo ``code``):
      SE001 – variable no declarada
      SE002 – redeclaración de variable en el mismo alcance
      SE003 – función no definida
      SE004 – aridad incorrecta en llamada a función
      SE005 – tipo incompatible en operación aritmética
      SE006 – return fuera del cuerpo de una función
      SE007 – operador lógico aplicado a tipo no booleano
      SE008 – condición de if/while no es booleana
    """

    code: str      # p. ej. "SE001"
    message: str
    line: int

