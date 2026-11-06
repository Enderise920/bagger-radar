import ast
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "app" / "dashboard.py").read_text(encoding="utf-8")
NAMES = {
    "n", "journal_report_fundamental_df", "journal_fundamental_forecast_df",
    "journal_fundamental_forecast_chart", "journal_fundamental_kpi_html",
}
tree = ast.parse(SOURCE)
nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in NAMES]
namespace = {"np": np, "pd": pd, "go": go}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(ROOT / "app" / "dashboard.py"), "exec"), namespace)


class FundamentalTtmTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "currency": "IDR",
            "financial_currency": "USD",
            "historical_financials": [
                {"year": 2024, "period_type": "FY", "revenue": 5_319_578_000, "earnings": 1_210_798_000},
                {"year": 2025, "period_type": "FY", "revenue": 4_910_263_000, "earnings": 760_180_000},
            ],
            "historical_eps": {"2026": {"eps": 1829.58, "period_type": "TTM"}},
            "ttm_financials": {
                "period_type": "TTM", "period_end": "2026-09-30", "quarters_used": 4,
                "revenue": 5_260_327_000, "earnings": 856_194_000, "eps": 1829.58,
            },
        }

    def test_ttm_is_visible_and_forecast_starts_next_year(self):
        hist = namespace["journal_report_fundamental_df"](self.report)
        current = hist.loc[hist.year.eq(2026)].iloc[0]
        self.assertEqual(current["kind"], "TTM")
        self.assertEqual(current["revenue"], 5_260_327_000)
        curve, meta = namespace["journal_fundamental_forecast_df"](
            self.report, hist, {"yoy_quarter_revenue_growth": .1, "yoy_quarter_earnings_growth": .1}
        )
        self.assertEqual(meta["forecast_years"], [2027, 2028, 2029])
        self.assertIn("TTM", set(curve["kind"]))

    def test_ttm_chart_and_currency_labels(self):
        hist = namespace["journal_report_fundamental_df"](self.report)
        curve, _ = namespace["journal_fundamental_forecast_df"](
            self.report, hist, {"yoy_quarter_revenue_growth": .1, "yoy_quarter_earnings_growth": .1}
        )
        fig = namespace["journal_fundamental_forecast_chart"](curve, "revenue", "Revenue", "money", "USD")
        self.assertIn("TTM", [trace.name for trace in fig.data])
        self.assertEqual(fig.layout.yaxis.title.text, "US$ B")
        kpi = namespace["journal_fundamental_kpi_html"](curve, "revenue", "money", "USD")
        self.assertIn("2026 TTM", kpi)
        self.assertIn("US$", kpi)


if __name__ == "__main__":
    unittest.main()
