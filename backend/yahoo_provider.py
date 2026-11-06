"""Yahoo Finance adapter for BAGGER RADAR.

The adapter keeps the existing JSON contracts.  yfinance is intentionally
imported lazily so the dashboard can still read local snapshots offline.
Yahoo Finance/yfinance is not an official redistribution API; production use
must be reviewed against Yahoo's terms before public deployment.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import math


def idx_symbol(symbol: str) -> str:
    value = str(symbol or "").upper().strip()
    return value if value.endswith(".JK") else f"{value}.JK"


def _clean(value: Any) -> Any:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return None
        if hasattr(value, "item"):
            value = value.item()
        return value
    except Exception:
        return None


def _yf():
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance belum terpasang; jalankan pip install -r requirements.txt") from exc
    return yf


def _info(ticker) -> dict:
    try:
        return ticker.get_info() or {}
    except Exception:
        try:
            return ticker.info or {}
        except Exception:
            return {}


def _ratio(info: dict, key: str) -> Any:
    return _clean(info.get(key))


def _decimal_yield(info: dict) -> Any:
    """Normalize Yahoo's occasionally percent-scaled dividend yield."""
    value = _ratio(info, "dividendYield")
    if isinstance(value, (int, float)) and value > 1:
        return value / 100.0
    return value


def fundamental_record(symbol: str, ticker=None) -> dict:
    symbol = idx_symbol(symbol)
    ticker = ticker or _yf().Ticker(symbol)
    info = _info(ticker)
    dividend_rate = _ratio(info, "dividendRate")
    return {
        "symbol": symbol,
        "company_name": info.get("longName") or info.get("shortName") or symbol,
        "market_cap": _ratio(info, "marketCap"),
        "roe_ttm": _ratio(info, "returnOnEquity"),
        "roa_ttm": _ratio(info, "returnOnAssets"),
        "pe_ttm": _ratio(info, "trailingPE"),
        "pb_mrq": _ratio(info, "priceToBook"),
        "forward_pe": _ratio(info, "forwardPE"),
        "yield_ttm": _decimal_yield(info),
        "dividend_ttm": dividend_rate,
        "yoy_quarter_revenue_growth": _ratio(info, "revenueGrowth"),
        "yoy_quarter_earnings_growth": _ratio(info, "earningsGrowth"),
    }


def profile_record(symbol: str, ticker=None) -> dict:
    symbol = idx_symbol(symbol)
    ticker = ticker or _yf().Ticker(symbol)
    info = _info(ticker)
    return {
        "symbol": symbol,
        "company_name": info.get("longName") or info.get("shortName") or symbol,
        "description": info.get("longBusinessSummary"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "source": "Yahoo Finance via yfinance",
        "source_url": f"https://finance.yahoo.com/quote/{symbol}",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


def daily_records(symbol: str, period: str = "1y", ticker=None) -> list[dict]:
    symbol = idx_symbol(symbol)
    ticker = ticker or _yf().Ticker(symbol)
    frame = ticker.history(period=period, auto_adjust=False, actions=False)
    if frame is None or frame.empty:
        return []
    rows = []
    for stamp, row in frame.iterrows():
        close = _clean(row.get("Close"))
        if close is None or close <= 0:
            continue
        rows.append({
            "symbol": symbol,
            "date": stamp.strftime("%Y-%m-%d"),
            "open": _clean(row.get("Open")), "high": _clean(row.get("High")),
            "low": _clean(row.get("Low")), "close": close,
            "volume": _clean(row.get("Volume")),
        })
    return rows


def _statement_value(frame, column, *labels):
    if frame is None or frame.empty:
        return None
    for label in labels:
        if label in frame.index:
            return _clean(frame.at[label, column])
    return None


def company_report(symbol: str, ticker=None) -> dict:
    """Return the dashboard's normalized report contract without fabrication."""
    symbol = idx_symbol(symbol)
    ticker = ticker or _yf().Ticker(symbol)
    info = _info(ticker)
    try: income = ticker.financials
    except Exception: income = None
    try: balance = ticker.balance_sheet
    except Exception: balance = None
    try: cashflow = ticker.cashflow
    except Exception: cashflow = None
    columns = []
    for frame in (income, balance, cashflow):
        if frame is not None and not frame.empty:
            columns.extend(list(frame.columns))
    columns = sorted(set(columns))
    historical = []
    eps = []
    for column in columns:
        record = {
            "year": int(getattr(column, "year", 0) or 0),
            "revenue": _statement_value(income, column, "Total Revenue"),
            "earnings": _statement_value(income, column, "Net Income", "Net Income Common Stockholders"),
            "ebit": _statement_value(income, column, "EBIT", "Operating Income"),
            "ebitda": _statement_value(income, column, "EBITDA", "Normalized EBITDA"),
            "gross_profit": _statement_value(income, column, "Gross Profit"),
            "total_assets": _statement_value(balance, column, "Total Assets"),
            "total_equity": _statement_value(balance, column, "Stockholders Equity", "Total Equity Gross Minority Interest"),
            "total_debt": _statement_value(balance, column, "Total Debt"),
            "cash_and_equivalents": _statement_value(balance, column, "Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"),
            "operating_cash_flow": _statement_value(cashflow, column, "Operating Cash Flow", "Total Cash From Operating Activities"),
            "capital_expenditure": _statement_value(cashflow, column, "Capital Expenditure", "Capital Expenditures"),
            "free_cash_flow": _statement_value(cashflow, column, "Free Cash Flow"),
        }
        if record["year"] and any(v is not None for k, v in record.items() if k != "year"):
            historical.append(record)
    historical.sort(key=lambda row: row["year"])
    trailing_eps = _ratio(info, "trailingEps")
    if trailing_eps is not None:
        eps.append({"year": datetime.now(timezone.utc).year, "eps": trailing_eps})
    return {
        "symbol": symbol,
        "company_name": info.get("longName") or info.get("shortName") or symbol,
        "sector": info.get("sector"), "industry": info.get("industry"), "sub_industry": None,
        "market_cap": _ratio(info, "marketCap"),
        "last_close_price": _ratio(info, "currentPrice") or _ratio(info, "regularMarketPrice"),
        "latest_close_date": None,
        "historical_financials": historical,
        "historical_eps": eps,
        "company_growth_forecasts": [],
        "dividend": {
            "dividend_ttm": _ratio(info, "dividendRate"),
            "yield_ttm": _decimal_yield(info),
            "payout_ratio": _ratio(info, "payoutRatio"),
            "cash_payout_ratio": None,
            "last_ex_dividend_date": _ratio(info, "exDividendDate"),
            "historical_dividends": [],
        },
        "valuation": {
            "pe_ttm": _ratio(info, "trailingPE"), "pb_mrq": _ratio(info, "priceToBook"),
            "forward_pe": _ratio(info, "forwardPE"), "intrinsic_value": None,
        },
        "management": {}, "ownership": {}, "peers": {}, "tags": [], "indices": [],
    }
