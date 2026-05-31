from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from mathlite.service import analyze_source

# ─────────────────────────────────────────────────────────────────────────
#  MongoDB Atlas (opcional)
#  La conexión se configura mediante variables de entorno; si no existen,
#  la API funciona igual pero sin persistir casos de prueba. Esto permite
#  desarrollar en local sin base de datos y desplegar con ella en la nube.
#
#  Variables de entorno esperadas:
#     MONGODB_URI  – cadena de conexión de MongoDB Atlas
#     MONGODB_DB   – nombre de la base de datos   (por defecto "mathlite")
# ─────────────────────────────────────────────────────────────────────────

MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB = os.getenv("MONGODB_DB", "mathlite")
CASES_COLLECTION = "test_cases"

_mongo_client = None
_db = None

try:
    if MONGODB_URI:
        from pymongo import MongoClient

        _mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        _db = _mongo_client[MONGODB_DB]
except Exception as exc:  # pragma: no cover - fallo de conexion no debe tumbar la API
    print(f"[MathLite] No se pudo conectar a MongoDB: {exc}")
    _db = None


def _persist_case(source: str, result: dict) -> None:
    """Guarda el caso analizado en MongoDB (si hay conexion)."""
    if _db is None:
        return
    try:
        _db[CASES_COLLECTION].insert_one(
            {
                "source": source,
                "ok": result.get("ok", False),
                "summary": {
                    "lexer_errors": len(result.get("lexer_errors", [])),
                    "parser_errors": len(result.get("parser_errors", [])),
                    "semantic_errors": len(result.get("semantic_errors", [])),
                    "runtime_errors": len(result.get("runtime_errors", [])),
                    "output_lines": len(result.get("output", [])),
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as exc:  # pragma: no cover
        print(f"[MathLite] No se pudo guardar el caso: {exc}")


# ─────────────────────────────────────────────────────────────────────────
#  Modelos de peticion
# ─────────────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    source: str = Field(default="")


# ─────────────────────────────────────────────────────────────────────────
#  Aplicacion
# ─────────────────────────────────────────────────────────────────────────

app = FastAPI(title="MathLite API", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "db": "connected" if _db is not None else "disabled"}


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest) -> dict:
    result = analyze_source(request.source)
    _persist_case(request.source, result)
    return result


@app.get("/api/cases")
def list_cases(limit: int = 20) -> dict:
    """Devuelve los ultimos casos de prueba almacenados en la base de datos."""
    if _db is None:
        return {"cases": [], "db": "disabled"}
    try:
        cursor = (
            _db[CASES_COLLECTION]
            .find({}, {"_id": 0})
            .sort("created_at", -1)
            .limit(max(1, min(limit, 100)))
        )
        return {"cases": list(cursor), "db": "connected"}
    except Exception as exc:  # pragma: no cover
        return {"cases": [], "db": "error", "detail": str(exc)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)