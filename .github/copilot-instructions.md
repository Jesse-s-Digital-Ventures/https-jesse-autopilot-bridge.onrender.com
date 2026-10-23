# Jesse Autopilot Bridge — GitHub Copilot Instructions

## 1. Project Context & Architecture
- **Service Name:** Jesse-Autopilot-Bridge
- **Runtime Environment:** Python 3 (FastAPI & Uvicorn)
- **Deployment Host:** Render Web Service (Region: Oregon)
- **Database:** MongoDB (Connected via Motor/PyMongo drivers)
- **Primary Domain:** fabulousgemsparlor.store (Mapped to this Python web service)
- **Primary Function:** Fully automated social media marketing backend that fetches Sellvia product feeds, runs AI caption generation (OpenAI & Anthropic Claude), and executes automated posts to Meta and TikTok.

## 2. Environment & Routing Standards
- Application must run using `uvicorn main:app --host 0.0.0.0 --port $PORT`.
- Keep the active `/healthz` endpoint returning health status and `"mongodb_connected": true`.
- Trigger endpoints (e.g., `/cron/rss-post`) MUST remain defined as HTTP `POST` routes. Do not change them to `GET`.
- Ensure FastAPI interactive OpenAPI documentation remains accessible at `/docs`.

## 3. Environment Variables & Secrets
Assume all operational logic depends on the following keys set in Render Environment Variables:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `TIKTOK_ACCESS_TOKEN`
- `MONGODB_URI`

## 4. Code Maintenance & Rules
- Write asynchronous, lightweight Python code (`async def` endpoint functions).
- Wrap all third-party API requests (OpenAI, Anthropic, TikTok, Meta) in robust try/except blocks with explicit error responses.
- Do NOT introduce Node.js, `package.json`, or JavaScript build steps; the service relies exclusively on Python 3 and `requirements.txt`.
