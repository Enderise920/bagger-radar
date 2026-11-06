import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import migrate_yahoo
from yahoo_provider import daily_records, fundamental_record, idx_symbol


class FakeTicker:
    def get_info(self):
        return {
            "longName": "Bank Contoh Tbk", "marketCap": 1000,
            "returnOnEquity": 0.2, "returnOnAssets": 0.05,
            "trailingPE": 10, "priceToBook": 2, "forwardPE": 9,
            "dividendYield": 0.03, "dividendRate": 30,
            "revenueGrowth": 0.1, "earningsGrowth": None,
        }

    def history(self, **kwargs):
        return pd.DataFrame(
            {"Open": [100.0], "High": [110.0], "Low": [99.0], "Close": [105.0], "Volume": [10000]},
            index=pd.to_datetime(["2026-11-04"]),
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

    def test_universe_reads_existing_company_contract(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as folder:
            path = Path(folder)
            (path / "companies.json").write_text(json.dumps([{"symbol": "bbca"}, {"symbol": "TLKM.JK"}]), encoding="utf-8")
            self.assertEqual(migrate_yahoo.universe(path), ["BBCA.JK", "TLKM.JK"])


if __name__ == "__main__":
    unittest.main()
