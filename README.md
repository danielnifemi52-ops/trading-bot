# RSI Trading Bot — Full-Stack Web Application

A complete, production-ready RSI-based stock trading bot with a live React dashboard, FastAPI backend, WebSocket streaming, SQLite persistence, and Telegram alerts.

---

## Features

- **Live RSI Trading**: Wilder's Smoothed RSI matching TradingView, with BUY/SELL/HOLD signals
- **Risk Management**: Position sizing based on account equity and stop-loss percentage
- **Dashboard**: Real-time RSI gauge, price ticker, account value, and signal badges
- **Backtester**: Walk-forward backtest with equity curve chart and full trade stats
- **Optimizer**: Async grid-search optimizer ranks parameter combos by Sharpe ratio
- **Trade History**: Filterable table with P&L colouring and per-trade delete
- **WebSocket**: Live bot data pushed to all connected browser tabs
- **Telegram Alerts**: Signal, trade closed, stop-loss, and hourly heartbeat messages
- **Dry-Run Mode**: Simulate all trades without touching a real Alpaca account

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, Uvicorn, SQLModel, SQLite |
| Data | yfinance, pandas, numpy |
| Broker | Alpaca Paper Trading API |
| Alerts | Telegram Bot API via httpx |
| Frontend | React 19, Vite, Recharts, React Router |
| Tests | pytest, pytest-asyncio, httpx TestClient |

---

## Project Structure

```
rsi_bot_web/
├── backend/
│   ├── main.py          # FastAPI app + CORS + API key middleware
│   ├── state.py         # Thread-safe singleton bot state
│   ├── db.py            # SQLite engine + session factory
│   ├── models.py        # SQLModel ORM + Pydantic schemas
│   ├── ws.py            # WebSocket connection manager
│   ├── core/
│   │   ├── strategy.py  # RSI math + BUY/SELL/HOLD signals
│   │   └── risk.py      # Stop-loss / take-profit helpers
│   ├── services/
│   │   ├── bot_runner.py  # Live polling loop (daemon thread)
│   │   ├── backtester.py  # Walk-forward backtest engine
│   │   ├── optimizer.py   # Grid-search optimizer
│   │   ├── broker.py      # Alpaca wrapper (dry-run safe)
│   │   └── alerts.py      # Telegram alerter
│   ├── routers/
│   │   ├── bot.py        # /api/bot/* endpoints
│   │   ├── backtest.py   # /api/backtest/* endpoints
│   │   ├── optimizer.py  # /api/optimizer/* endpoints
│   │   └── trades.py     # /api/trades/* endpoints
│   └── tests/            # 35 passing tests
│
└── frontend/
    └── src/
        ├── api/client.js       # Axios instance + all API calls
        ├── hooks/              # useBot, useBacktest, useOptimizer
        ├── components/         # Layout, StatCard, RSIGauge, EquityChart, BotControls, SignalBadge
        ├── pages/              # Dashboard, Backtest, Optimizer, Trades
        └── styles/globals.css  # Dark mode design tokens
```

---

## Local Development

### 1. Backend

```bash
cd rsi_bot_web/backend
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
cp .env.example .env         # Fill in your keys
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd rsi_bot_web/frontend
npm install
cp .env.example .env.local   # Edit VITE_API_URL if needed
npm run dev
```

Dashboard: http://localhost:5173

### 3. Run Tests

```bash
cd rsi_bot_web/backend
pytest tests/ -v              # All 35 tests must pass
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `ALPACA_KEY` | Alpaca API key |
| `ALPACA_SECRET` | Alpaca secret key |
| `ALPACA_PAPER` | Set `true` for paper trading |
| `TELEGRAM_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |
| `API_KEY` | Optional: secures `/api/*` with `X-API-Key` header |
| `CORS_ORIGIN` | Frontend URL (e.g. `https://your-app.vercel.app`) |
| `DATABASE_URL` | SQLite path (default: `sqlite:///./rsi_bot.db`) |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend URL (e.g. `https://your-api.onrender.com`) |
| `VITE_WS_URL` | WebSocket URL (`wss://your-api.onrender.com`) |
| `VITE_API_KEY` | Must match backend `API_KEY` if set |

---

## Deployment

### Backend → Render

1. Create a new **Web Service** pointing to this repo
2. Set **Root Directory** to `backend`
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add all environment variables from the table above
6. Set `ALPACA_PAPER=true` until you have 30+ days of paper results

### Frontend → Vercel

1. Import repo, set **Root Directory** to `frontend`
2. Framework preset: **Vite**
3. Add `VITE_API_URL` and `VITE_WS_URL` pointing to your Render URL
4. Deploy — Vercel handles the rest

---

## ⚠️ Important Safety Notes

- **Never commit `.env`** — it is in `.gitignore`
- **Always paper-trade first** (`ALPACA_PAPER=true`)
- The bot defaults to `dry_run=true` from the UI — you must opt in to live orders
- RSI signals are a starting point, not financial advice

---

## License

MIT
