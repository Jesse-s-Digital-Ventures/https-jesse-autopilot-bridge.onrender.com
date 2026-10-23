# Domain & Runtime Rules for fabulousgemsparlor.store

## Environment & Server Mapping
- **Primary Domain:** fabulousgemsparlor.store
- **Backend Service:** Jesse-Autopilot-Bridge
- **Runtime Environment:** Python 3 (FastAPI & Uvicorn)

## Strict Constraints
1. **Python Only:** The domain `fabulousgemsparlor.store` routes exclusively to `main.py`.
2. **No Node.js:** Do NOT create `app.js`, `server.js`, or `package.json` for this domain.
3. **Execution Command:** Service must run via `uvicorn main:app --host 0.0.0.0 --port $PORT`.
