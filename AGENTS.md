# Repository Guidelines

## Project Structure & Module Organization

- `backend/main.py` starts the FastAPI app, middleware, and router registration.
- `backend/core/` contains trading logic such as RSI strategy and risk helpers.
- `backend/services/` contains broker, bot runner, backtesting, optimizer, and alert integrations.
- `backend/routers/` exposes API routes for bot control, backtests, optimizer, and trades.
- `backend/tests/` contains pytest coverage for routes, strategy, WebSockets, and backtesting.
- `frontend/src/` contains the Vite React app. Use `components/` for reusable UI, `pages/` for routed screens, `hooks/` for stateful API logic, and `api/client.js` for backend calls.
- `frontend/public/` and `frontend/src/assets/` hold static assets.

## Build, Test, and Development Commands

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
pytest tests/ -v
```

Frontend:

```bash
cd frontend
npm install
npm run dev
npm run build
npm run lint
npm run preview
```

`npm run dev` starts Vite, `npm run build` creates the production bundle, and `npm run lint` runs ESLint.

## Coding Style & Naming Conventions

Keep Python modules small and organized by responsibility. Use snake_case for Python files, functions, and variables. Name route modules after their domain, such as `bot.py` or `trades.py`.

Use React function components with PascalCase filenames, such as `RSIGauge.jsx` and `Dashboard.jsx`. Use camelCase for helpers and prefix hooks with `use`, such as `useBot.js`.

Follow the existing JavaScript style: ES modules, JSX, two-space indentation in frontend files, and ESLint rules from `frontend/eslint.config.js`.

## Testing Guidelines

Backend tests use `pytest` and `pytest-asyncio`. Add tests under `backend/tests/` with names like `test_strategy.py` and functions named `test_*`. Prefer focused tests for trading math, API behavior, WebSocket updates, and regression cases around bot state.

Run `pytest tests/ -v` from `backend` before backend changes. Run `npm run lint` and `npm run build` from `frontend` before frontend changes.

## Commit & Pull Request Guidelines

Use concise Conventional Commit-style subjects seen in history, for example:

```text
fix: prevent dashboard flickering on loading
feat: add optimizer results export
```

Pull requests should include a short summary, test commands run, linked issues when applicable, and screenshots for UI changes. Call out changes that affect live trading, broker behavior, credentials, or environment variables.

## Security & Configuration Tips

Never commit `.env`, `.env.local`, API keys, Telegram tokens, Alpaca credentials, SQLite database files, or generated build output. Keep `ALPACA_PAPER=true` and dry-run behavior enabled when testing broker-related changes.
