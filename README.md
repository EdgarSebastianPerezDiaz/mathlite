# MathLite

## Arranque local en Windows

El proyecto se divide en dos partes:

- Backend Python en `backend/`
- Frontend Angular en `frontend/`

## Requisitos

- Python 3.14 o compatible
- Node.js 18 o superior
- npm

## 1) Levantar el backend

Abre una terminal de PowerShell en la carpeta raíz del proyecto y ejecuta:

```powershell
cd "c:\Users\botia\OneDrive\Desktop\Septimo\Lenguajes Formales\Proyecto"
.\.venv\Scripts\Activate.ps1
cd backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Si PowerShell bloquea la activación de la virtualenv, ejecuta primero:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

El backend quedará disponible en:

- `http://localhost:8000/health`
- `http://localhost:8000/api/analyze`

## 2) Levantar el frontend

Abre otra terminal de PowerShell y ejecuta:

```powershell
cd "c:\Users\botia\OneDrive\Desktop\Septimo\Lenguajes Formales\Proyecto\frontend"
npm install
npm start
```

Si PowerShell bloquea la ejecución de scripts (error sobre `npm.ps1`), puedes hacer cualquiera de las siguientes opciones:

- Ejecutar temporalmente con permisos de ejecución en la sesión actual:

cd "c:\Users\botia\OneDrive\Desktop\Septimo\Lenguajes Formales\Proyecto\frontend"
npm install
npm start
```

La aplicación quedará disponible en:

- `http://localhost:4200`

## 3) Orden recomendado de uso

1. Inicia el backend primero.
2. Inicia el frontend después.
3. Abre `http://localhost:4200` y usa el editor para enviar código MathLite.

## 4) Verificación rápida

Si el sistema está bien levantado, deberías poder:

- abrir `http://localhost:8000/health` y ver `{"status":"ok"}`
- enviar código desde la interfaz y recibir tokens, diagnósticos y AST
