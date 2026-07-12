# Arbiscan Web App — Running the SaaS stack

Two processes in development: the **Django API** and the **React SPA**.

## 1. Backend API (Django + DRF)

```bash
cd arbiscan
venv\Scripts\activate
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Key endpoints:

| Endpoint | Tier | Purpose |
|---|---|---|
| `POST /api/calc/` | **Free** | Arbitrage calculator (odds → stakes + profit) |
| `POST /api/auth/register/` | Free | Create account, returns JWT |
| `POST /api/auth/token/` | Free | Log in (JWT) |
| `GET  /api/auth/me/` | Auth | Current user + subscription |
| `POST /api/auth/checkout/` | Auth | Upgrade (billing stub) |
| `GET  /api/live/sure-bets/?target=500` | **Freemium** | Live sure-bets; free sees ≤`FREE_ARB_ROI_CAP`% ROI + a locked count, premium sees all |
| `GET  /api/arbs/`, `/api/fixtures/…` | Premium | Raw live data |

Grant premium (no real billing yet):
```bash
python manage.py grant_premium <username> --days 30
```
…or via the Django admin → Subscriptions → "Grant premium (30 days)".

## 2. Frontend SPA (React + Vite)

```bash
cd frontend
npm install      # first time
npm run dev      # http://localhost:5173
```

Pages: **Calculator** (free, public), **Login/Register**, **Live Sure-Bets**
(premium — shows an upgrade prompt for free users), **Pricing**.

The SPA calls the API at `http://localhost:8000/api` by default; override with a
`frontend/.env` containing `VITE_API_BASE=...`. CORS is pre-configured for
`localhost:5173` (see `CORS_ALLOWED_ORIGINS` in settings / `.env`).

## Architecture & roadmap

Free calculator is pure computation (`odds/services/calculator.py`). Premium live
data reuses the existing scan/report pipeline (`odds/services/reporting.py`).
Billing is a pluggable interface (`accounts/billing.py`) — today a manual provider;
M-Pesa (Paystack/IntaSend) or Stripe drop in behind the same `BillingProvider`
without touching the rest of the app. Next steps: real payments + scheduled scans
feeding the live feed (the "data stream"). See `arbiscan/ENGINEERING_AUDIT.md`.
