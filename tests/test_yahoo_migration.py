import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import migrate_yahoo
from yahoo_provider import company_report, daily_records, fundamental_record, idx_symbol


class FakeTicker:
    def get_info(self):
        return {
            "longName": "Bank Contoh Tbk", "marketCap": 1000,
            "returnOnEquity": 0.2, "returnOnAssets": 0.05,
            "trailingPE": 10, "priceToBook": 2, "forwardPE": 9,
            "dividendYield": 0.03, "dividendRate": 30,
            "revenueGrowth": 0.1, "earningsGrowth": None, "trailingEps": 55.0,
        }

    def history(self, **kwargs):
        return pd.DataFrame(
            {"Open": [100.0], "High": [110.0], "Low": [99.0], "Close": [105.0], "Volume": [10000]},
            index=pd.to_datetime(["2026-11-04"]),
        )

    @property
    def financials(self):
        column = pd.Timestamp("2025-12-31")
        return pd.DataFrame(
            {column: [1_000_000.0, 100_000.0, 50.0, 2_000.0]},
            index=["Total Revenue", "Net Income", "Diluted EPS", "Diluted Average Shares"],
        )

    @property
    def balance_sheet(self):
        return pd.DataFrame()

    @property
    def cashflow(self):
        return pd.DataFrame()

    @property
    def dividends(self):
        return pd.Series(
            [10.0, 15.0, 20.0],
            index=pd.to_datetime(["2024-06-01", "2024-12-01", "2025-06-01"]),
        )


class YahooContractTests(unittest.TestCase):
    def test_idx_symbol_is_idempotent(self):
        self.assertEqual(idx_symbol("bbca"), "BBCA.JK")
        self.assertEqual(idx_symbol("BBCA.JK"), "BBCA.JK")

    def test_fundamental_contract_preserves_missing(self):
        row = fundamental_record("BBCA", FakeTicker())
        self.assertEqual(row["symbol"], "BBCA.JK")
        self.assertEqual(row["roe_ttm"], 0.2)
        self.assertIsNone(row["yoy_quarter_earnings_growth"])

    def test_daily_contract(self):
        rows = daily_records("BBCA", ticker=FakeTicker())
        self.assertEqual(rows[0]["date"], "2026-11-04")
        self.assertEqual(rows[0]["close"], 105.0)

    def test_company_report_eps_and_dividend_contract(self):
        report = company_report("BBCA", FakeTicker())
        self.assertEqual(report["historical_eps"]["2025"]["eps"], 50.0)
        dividends = report["dividend"]["historical_dividends"]
        self.assertEqual(dividends["2024"]["total_dividend"], 25.0)
        self.assertEqual(dividends["2024"]["payments"], 2)

    def test_company_report_omits_mismatched_currency_annual_eps(self):
        ticker = FakeTicker()
        original = ticker.get_info
        ticker.get_info = lambda: {**original(), "currency": "IDR", "financialCurrency": "USD"}
        report = company_report("AADI", ticker)
        self.assertNotIn("2025", report["historical_eps"])
        self.assertIn("2026", report["historical_eps"])
        self.assertFalse(report["statement_currency_comparable"])

    def test_universe_reads_existing_company_contract(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as folder:
            path = Path(folder)
            (path / "companies.json").write_text(json.dumps([{"symbol": "bbca"}, {"symbol": "TLKM.JK"}]), encoding="utf-8")
            self.assertEqual(migrate_yahoo.universe(path), ["BBCA.JK", "TLKM.JK"])

    def test_aadi_curated_industry_peers_exist_in_dashboard_universe(self):
        groups = json.loads((ROOT / "data" / "local_peer_groups.json").read_text(encoding="utf-8"))["groups"]
        aadi_peers = set(groups["AADI.JK"]["peer_symbols"])
        fundamentals = json.loads((ROOT / "data" / "fundamentals.json").read_text(encoding="utf-8"))
        available = {row["symbol"] for row in fundamentals if isinstance(row, dict) and row.get("symbol")}
        self.assertEqual(aadi_peers, {"PTBA.JK", "ITMG.JK", "BYAN.JK", "BUMI.JK", "HRUM.JK"})
        self.assertTrue(aadi_peers.issubset(available))


if __name__ == "__main__":
    unittest.main()
