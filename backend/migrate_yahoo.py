"""Build Yahoo-compatible BAGGER RADAR snapshots and a per-field gap report."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from yahoo_provider import company_report, daily_records, fundamental_record, idx_symbol, profile_record


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default


def atomic_write(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def universe(data_dir: Path) -> list[str]:
    rows = load(data_dir / "companies.json", []) or load(data_dir / "fundamentals.json", [])
    values = rows.keys() if isinstance(rows, dict) else (r.get("symbol") for r in rows if isinstance(r, dict))
    return sorted({idx_symbol(v) for v in values if v})


def coverage(rows: list[dict], fields: list[str]) -> dict:
    total = len(rows)
    return {field: {"available": sum(r.get(field) is not None for r in rows), "total": total} for field in fields}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--limit", type=int, default=0, help="0 means the complete local IDX universe")
    parser.add_argument("--period", default="1y")
    parser.add_argument("--with-reports", action="store_true", help="slower annual-statement cache")
    args = parser.parse_args(argv)
    symbols = universe(args.data_dir)[: args.limit or None]
    fundamentals, profiles, daily, reports, failures = [], [], {}, {}, {}
    for number, symbol in enumerate(symbols, 1):
        print(f"[{number}/{len(symbols)}] {symbol}")
        try: fundamentals.append(fundamental_record(symbol))
        except Exception as exc: failures.setdefault(symbol, {})["fundamentals"] = str(exc)
        try: profiles.append(profile_record(symbol))
        except Exception as exc: failures.setdefault(symbol, {})["profile"] = str(exc)
        try: daily[symbol] = daily_records(symbol, args.period)
        except Exception as exc: failures.setdefault(symbol, {})["daily"] = str(exc)
        if args.with_reports:
            try:
                reports[symbol] = {"source": "Yahoo Finance via yfinance", "fetched_at": datetime.now(timezone.utc).isoformat(), "api_status": "ok", "report": company_report(symbol)}
            except Exception as exc: failures.setdefault(symbol, {})["report"] = str(exc)
    atomic_write(args.data_dir / "fundamentals.yahoo.json", fundamentals)
    atomic_write(args.data_dir / "company_profiles.yahoo.json", profiles)
    atomic_write(args.data_dir / "daily_cache.yahoo.json", daily)
    if args.with_reports: atomic_write(args.data_dir / "journal_report_cache.yahoo.json", reports)
    fields = ["market_cap", "roe_ttm", "roa_ttm", "pe_ttm", "pb_mrq", "forward_pe", "yield_ttm", "dividend_ttm", "yoy_quarter_revenue_growth", "yoy_quarter_earnings_growth"]
    status = {"generated_at": datetime.now(timezone.utc).isoformat(), "source": "Yahoo Finance via yfinance", "symbols_requested": len(symbols), "fundamentals_received": len(fundamentals), "profiles_received": len(profiles), "daily_symbols_received": sum(bool(v) for v in daily.values()), "coverage": coverage(fundamentals, fields), "failures": failures}
    atomic_write(args.data_dir / "yahoo_migration_status.json", status)
    print(json.dumps({k: status[k] for k in ("symbols_requested", "fundamentals_received", "profiles_received", "daily_symbols_received")}, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
