# LangGraph Symptom Triage Assistant

Interactive multi-agent symptom triage demo with a React frontend, FastAPI backend, Groq-backed LangGraph workflow, and an animated node-flow visualization.

This app is for learning and demonstration only. It does not provide medical diagnosis or replace professional medical care.

## What It Shows

- Guided symptom intake with required fields and demo scenarios
- FastAPI validation and safe triage responses
- LangGraph `StateGraph` with visible workflow nodes
- Animated flow across Intake, Symptom Analyzer, Care Guidance, Supervisor, and Final Response
- Groq LLM support with deterministic fallback
- Optional local persistence, disabled by default for free hosting
- Developer trace accordion for agent JSON outputs

## Project Layout

```text
backend/      FastAPI, LangGraph, SQLAlchemy, tests
frontend/     React + Vite + TypeScript UI
docker-compose.yml
render.yaml
```

## Environment

Copy the backend example environment file:

```bash
cp backend/.env.example backend/.env
```

Recommended local/demo settings:

```env
DATABASE_URL=sqlite:///./triage_dev.db
PERSIST_CASES=false
LLM_PROVIDER=groq
GROQ_API_KEY=your_rotated_key_here
LLM_MODEL=openai/gpt-oss-20b
LLM_BASE_URL=https://api.groq.com/openai/v1
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

Keep API keys only in `backend/.env` or your deployment provider's secret environment variables. Do not put keys in frontend files or commit them.

## Run Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Backend API docs:

```text
http://127.0.0.1:8000/docs
```

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://127.0.0.1:5173
```

## Test

```bash
cd backend
source .venv/bin/activate
pytest
```

```bash
cd frontend
npm run build
```

## Free Hosting

Recommended permanent split:

- Frontend: Vercel free static hosting
- Backend: Render free web service
- Database: none for public demo, using `PERSIST_CASES=false`

Frontend environment variable:

```env
VITE_API_BASE=https://your-render-service.onrender.com
```

Render backend environment variables:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_rotated_key_here
LLM_MODEL=openai/gpt-oss-20b
LLM_BASE_URL=https://api.groq.com/openai/v1
PERSIST_CASES=false
CORS_ORIGINS=https://your-vercel-app.vercel.app
```

Render start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Free hosting tradeoffs: Render free services can sleep after inactivity, first requests after sleep may be slow, and Groq free API limits still apply.

### Option A: Vercel Frontend + Render Backend

This is the recommended setup because the app has both a React frontend and a FastAPI backend.

1. Push this project to GitHub.
2. In Render, create a new Blueprint/Web Service from the repo. The included `render.yaml` config deploys the backend from `backend/`.
3. Set Render environment variables:

```env
GROQ_API_KEY=your_rotated_groq_key_here
CORS_ORIGINS=https://your-vercel-app.vercel.app
PERSIST_CASES=false
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-20b
LLM_BASE_URL=https://api.groq.com/openai/v1
```

4. In Vercel, import the same repo and set the project root to `frontend`.
5. Set Vercel environment variable:

```env
VITE_API_BASE=https://your-render-service.onrender.com
```

6. Redeploy Vercel after the Render URL is known.

### Option B: GitHub Pages Frontend + Render Backend

GitHub Pages can host only the static frontend. The FastAPI backend still needs Render, Railway, Fly.io, or another server host.

This repo includes `.github/workflows/deploy-frontend-pages.yml`. To use it:

1. Push this project to a GitHub repo using the `main` branch.
2. In the GitHub repo, enable Pages with GitHub Actions as the source.
3. Add a repository secret named `VITE_API_BASE` with your Render backend URL.
4. Push to `main` or manually run the workflow.

### Security Note

If a real API key was ever committed or shared, rotate it before deploying. Keep actual keys only in `.env` files or provider secret settings, never in `.env.example`.
