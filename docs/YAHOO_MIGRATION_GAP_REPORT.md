# BAGGER RADAR — Yahoo Finance migration audit

Audit date: 2026-11-05 (Asia/Jakarta)

## Audited runtime datasets

The dashboard directly loads these canonical files:

| Dashboard key | File | Shape | Existing coverage |
|---|---|---:|---:|
| `bagger` | `bagger_scores.json` | list | 962 symbols |
| `fund` | `fundamentals.json` | list | 962 symbols |
| `momentum` | `momentum_scores.json` | symbol map | 514 symbols |
| `risk` | `risk_metrics.json` | symbol map | 518 symbols |
| `profile` | `company_profiles.json` | list | 962 symbols |
| `daily` | `daily_cache.json` | symbol map | 552 symbols |

`journal_report_cache.json` is a seventh runtime cache used by Company Journal.

Existing Sectors-derived fundamental coverage before migration:

| Field | Non-null |
|---|---:|
| market cap | 962/962 (100.0%) |
| ROE / ROA | 861/962 (89.5%) each |
| trailing PE | 863/962 (89.7%) |
| price-to-book | 897/962 (93.2%) |
| forward PE | 137/962 (14.2%) |
| dividend yield | 487/962 (50.6%) |
| dividend TTM | 330/962 (34.3%) |
| quarterly revenue growth | 814/962 (84.6%) |
| quarterly earnings growth | 822/962 (85.4%) |

## Field mapping

| Existing field | Yahoo/yfinance source | Result |
|---|---|---|
| OHLCV | `Ticker.history()` | Available when Yahoo covers the `.JK` symbol |
| `market_cap` | `marketCap` | Usually available; point-in-time only |
| `roe_ttm`, `roa_ttm` | `returnOnEquity`, `returnOnAssets` | Partial coverage |
| `pe_ttm`, `pb_mrq`, `forward_pe` | `trailingPE`, `priceToBook`, `forwardPE` | Partial coverage; negative earnings commonly produce null PE |
| `yield_ttm`, `dividend_ttm` | `dividendYield`, `dividendRate` | Partial coverage |
| quarterly revenue/earnings growth | `revenueGrowth`, `earningsGrowth` | Partial and not guaranteed to match the former vendor period definition |
| sector, industry, description | `sector`, `industry`, `longBusinessSummary` | Partial; Yahoo taxonomy differs from IDX/Sectors |
| annual statements | `financials`, `balance_sheet`, `cashflow` | Partial, normally limited annual history |
| momentum/risk metrics | calculated from Yahoo OHLCV | Available only with sufficient valid trading history |
| Bagger Score | existing deterministic scoring engine | Recalculate locally; not a Yahoo field |

## Unavailable or non-equivalent fields

These must remain null/empty unless another licensed source is added:

- Sectors intrinsic value and vendor forecasts.
- Cash payout ratio with the former vendor's locked definition.
- Complete management, ownership, peer, tag, and index membership structures.
- Sectors sub-industry taxonomy and sector membership equivalence.
- A guaranteed complete list of all IDX listings, delistings, suspensions, and ticker changes.
- Restated point-in-time statements and a guarantee that Yahoo periods/units match the former provider.
- Annual EPS from issuers whose Yahoo statement currency differs from the quote currency. These values are omitted unless an explicit FX conversion policy is added; trailing quote-currency EPS may still be shown.
- Redistribution rights for a public product. `yfinance` is an unofficial client; technical access is not permission to republish.

Missing data is retained as `null` and must never be converted to zero for scoring.

## Migration artifacts

- `backend/yahoo_provider.py`: compatible adapter for fundamentals, profiles, OHLCV, and Company Journal reports.
- `backend/migrate_yahoo.py`: complete-universe snapshot builder with atomic writes and `yahoo_migration_status.json`.
- `backend/data_loader.py` and `backend/daily_cache.py`: switched from Sectors to Yahoo.
- `app/dashboard.py`: runtime sector lookup, Company Report, daily refresh, and live price no longer require a Sectors key.
- `tests/test_yahoo_migration.py`: offline contract tests with a fake ticker.

Generated Yahoo snapshots use `.yahoo.json` suffixes. They do not overwrite reviewed canonical datasets automatically. Promote them only after coverage and score-drift review.

An end-to-end smoke run for `AADI.JK` on 2026-11-05 successfully produced fundamentals, profile, and one month of daily prices. This proves connectivity and the output contract, not full-universe coverage. The complete 962-symbol run remains intentionally separate because it is slow, rate-limit sensitive, and must be reviewed before promotion.
