# BAGGER RADAR / RowletAI

Streamlit research dashboard for Indonesian equities. It combines versioned data snapshots with deterministic scoring across growth, quality, valuation, momentum, and risk.

## Data architecture

- Yahoo Finance through `yfinance` supplies experimental `.JK` fundamentals, profiles, and OHLCV snapshots.
- Momentum, risk, evidence quality, and Bagger Score are calculated locally.
- The dashboard reads reviewed JSON snapshots instead of downloading the full IDX universe on each page visit.
- Missing fields remain null; they are not converted to zero.

`yfinance` is an unofficial Yahoo Finance client. Technical access does not automatically grant redistribution rights. Review the terms of every source before making data public.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app/dashboard.py
```

The dashboard does not require a Sectors API key. Optional image and logo credentials are documented in `.env.example`; keep actual values outside Git.

## Refresh Yahoo snapshots

```powershell
# One-symbol test
python backend/migrate_yahoo.py --limit 1 --period 1mo

# Complete locally known IDX universe
python backend/migrate_yahoo.py --period 1y --with-reports
```

The command creates `*.yahoo.json` candidates and `yahoo_migration_status.json`. It does not overwrite canonical dashboard datasets. Review coverage and score drift before promoting candidates.

## Deploy

1. Create a private GitHub repository.
2. Push this project without `.env` or `.streamlit/secrets.toml`.
3. In Streamlit Community Cloud, create an app from that repository.
4. Set the entrypoint to `app/dashboard.py`.
5. Deploy, inspect logs, and test every page before considering public access.

See [deployment checklist](docs/DEPLOYMENT.md) and [migration gap report](docs/YAHOO_MIGRATION_GAP_REPORT.md).

This project is an analytical research tool, not investment advice.
