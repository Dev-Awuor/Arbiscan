# Arbiscan Web App

Two processes in development: the **Django API** and the **React SPA**.

## 1. Backend API (Django + DRF)

```bash
cd arbiscan
venv\Scripts\activate
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

| Endpoint | Access | Purpose |
|---|---|---|
| `POST /api/calc/` | Public | Arbitrage calculator (odds → stakes + profit) |
| `POST /api/auth/register/` | Public | Create account, returns JWT |
| `POST /api/auth/token/` | Public | Log in (JWT) |
| `GET  /api/auth/me/` | Login | Current user |
| `GET  /api/stats/` | Login | Pipeline health + arb summary for the dashboard |
| `GET  /api/live/sure-bets/?target=500&market=H2H` | Login | Open arbs, sized to the target profit |
| `GET  /api/arbs/`, `/api/fixtures/…` | Login | Raw data |

There are no paid tiers: any logged-in user sees everything.

## 2. Frontend SPA (React + Vite)

```bash
cd frontend
npm install      # first time
npm run dev      # http://localhost:5173
```

- `/` public landing page (with a client-side bet-slip demo)
- `/login`, `/register`
- `/app` dashboard behind login: Overview, Sure bets, Calculator, Guide

The SPA calls `http://localhost:8000/api` by default; override with `VITE_API_BASE` in `frontend/.env`.

## Refreshing data

```bash
python manage.py fetch_odds --leagues all --books pinnacle bet365 1xbet betsson unibet betika
python manage.py scan_arbs
```

`fetch_odds` batches tournaments into one OddsPapi call per bookmaker (10 tournaments per call),
trims responses to the scanned markets before caching, skips fixtures that have started, and
saves with bulk upserts. `scan_arbs` replaces the previous cross-book results on every run.
