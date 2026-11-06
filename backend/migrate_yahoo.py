"""Resumable Yahoo cache updater for the complete local IDX universe."""
from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from yahoo_provider import company_report, daily_records, fundamental_record, idx_symbol, profile_record

ROOT = Path(__file__).resolve().parents[1]
FUND_FIELDS = ["market_cap", "roe_ttm", "roa_ttm", "pe_ttm", "pb_mrq", "forward_pe", "yield_ttm", "dividend_ttm", "yoy_quarter_revenue_growth", "yoy_quarter_earnings_growth"]


def load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


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


def keyed(rows) -> dict[str, dict]:
    if isinstance(rows, dict):
        return {idx_symbol(k): v for k, v in rows.items()}
    return {idx_symbol(row.get("symbol")): row for row in rows if isinstance(row, dict) and row.get("symbol")}


def write_gaps(path: Path, symbols, fundamentals, profiles, daily, reports):
    fields = ["fundamentals", "profile", "daily", "annual_financials", "ttm_financials", "historical_eps", "dividends"]
    rows = []
    for symbol in symbols:
        report = (reports.get(symbol) or {}).get("report") or {}
        available = {
            "fundamentals": bool(fundamentals.get(symbol)), "profile": bool(profiles.get(symbol)),
            "daily": bool(daily.get(symbol)), "annual_financials": bool(report.get("historical_financials")),
            "ttm_financials": bool(report.get("ttm_financials")), "historical_eps": bool(report.get("historical_eps")),
            "dividends": bool((report.get("dividend") or {}).get("historical_dividends")),
        }
        rows.append({"symbol": symbol, **{field: "available" if available[field] else "unavailable" for field in fields}})
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["symbol", *fields]); writer.writeheader(); writer.writerows(rows)
    temp.replace(path)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--limit", type=int, default=0, help="Maximum symbols this run; 0 means all")
    parser.add_argument("--batch-size", type=int, default=0, help="Rotating batch size for scheduled runs")
    parser.add_argument("--period", default="1y")
    parser.add_argument("--with-reports", action="store_true")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.15)
    args = parser.parse_args(argv)

    data_dir = args.data_dir
    symbols = universe(data_dir)
    state_path = data_dir / "yahoo_update_state.json"
    state = load(state_path, {})
    start = int(state.get("next_offset", 0)) % max(len(symbols), 1) if args.batch_size else 0
    count = args.batch_size or args.limit or len(symbols)
    selected = (symbols[start:] + symbols[:start])[:count]
    fundamentals = keyed(load(data_dir / "fundamentals.yahoo.json", []))
    profiles = keyed(load(data_dir / "company_profiles.yahoo.json", []))
    daily = load(data_dir / "daily_cache.yahoo.json", {})
    reports = load(data_dir / "journal_report_cache.yahoo.json", {})
    failures = {}
    import yfinance as yf

    for number, symbol in enumerate(selected, 1):
        print(f"[{number}/{len(selected)}] {symbol}", flush=True)
        ticker = yf.Ticker(symbol)
        try:
            record = fundamental_record(symbol, ticker)
            if not any(record.get(field) is not None for field in FUND_FIELDS):
                raise ValueError("Yahoo returned no usable fundamental fields")
            fundamentals[symbol] = record
        except Exception as exc:
            failures.setdefault(symbol, {})["fundamentals"] = str(exc)
        try:
            record = profile_record(symbol, ticker)
            if not record.get("company_name") or record.get("company_name") == symbol:
                raise ValueError("Yahoo returned no company identity")
            profiles[symbol] = record
        except Exception as exc:
            failures.setdefault(symbol, {})["profile"] = str(exc)
        try:
            rows = daily_records(symbol, args.period, ticker)
            if not rows:
                raise ValueError("Yahoo returned no price history")
            daily[symbol] = rows
        except Exception as exc:
            failures.setdefault(symbol, {})["daily"] = str(exc)
        if args.with_reports:
            try:
                report = company_report(symbol, ticker)
                if not (report.get("historical_financials") or report.get("ttm_financials") or report.get("historical_eps")):
                    raise ValueError("Yahoo returned no statement, TTM or EPS evidence")
                reports[symbol] = {"source": "Yahoo Finance via yfinance", "fetched_at": datetime.now(timezone.utc).isoformat(), "api_status": "ok", "schema_version": 2, "report": report}
            except Exception as exc:
                failures.setdefault(symbol, {})["report"] = str(exc)
        if args.sleep:
            time.sleep(args.sleep)

    fund_rows = [fundamentals[key] for key in sorted(fundamentals)]
    profile_rows = [profiles[key] for key in sorted(profiles)]
    atomic_write(data_dir / "fundamentals.yahoo.json", fund_rows)
    atomic_write(data_dir / "company_profiles.yahoo.json", profile_rows)
    atomic_write(data_dir / "daily_cache.yahoo.json", daily)
    if args.with_reports:
        atomic_write(data_dir / "journal_report_cache.yahoo.json", reports)

    if args.publish:
        active_fund = keyed(load(data_dir / "fundamentals.json", [])); active_fund.update({s: fundamentals[s] for s in selected if s in fundamentals})
        active_profiles = keyed(load(data_dir / "company_profiles.json", [])); active_profiles.update({s: profiles[s] for s in selected if s in profiles})
        active_daily = load(data_dir / "daily_cache.json", {}); active_daily.update({s: daily[s] for s in selected if s in daily})
        atomic_write(data_dir / "fundamentals.json", [active_fund[key] for key in sorted(active_fund)])
        atomic_write(data_dir / "company_profiles.json", [active_profiles[key] for key in sorted(active_profiles)])
        atomic_write(data_dir / "daily_cache.json", active_daily)
        if args.with_reports:
            active_reports = load(data_dir / "journal_report_cache.json", {}); active_reports.update({s: reports[s] for s in selected if s in reports})
            atomic_write(data_dir / "journal_report_cache.json", active_reports)

    next_offset = (start + len(selected)) % max(len(symbols), 1)
    status = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "source": "Yahoo Finance via yfinance",
        "universe_size": len(symbols), "batch_start": start, "symbols_requested": len(selected), "next_offset": next_offset,
        "published": args.publish, "reports_requested": args.with_reports, "fundamentals_cached": len(fundamentals),
        "profiles_cached": len(profiles), "daily_symbols_cached": sum(bool(v) for v in daily.values()), "reports_cached": len(reports),
        "coverage": coverage(fund_rows, FUND_FIELDS), "failures": failures,
    }
    atomic_write(data_dir / "yahoo_migration_status.json", status)
    atomic_write(state_path, {"next_offset": next_offset, "last_run": status["generated_at"], "universe_size": len(symbols)})
    write_gaps(data_dir / "yahoo_data_gap_report.csv", symbols, fundamentals, profiles, daily, reports)
    print(json.dumps({k: status[k] for k in ("universe_size", "symbols_requested", "next_offset", "fundamentals_cached", "daily_symbols_cached", "reports_cached")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
