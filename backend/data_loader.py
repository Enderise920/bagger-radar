import json
from pathlib import Path

from yahoo_provider import fundamental_record


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

COMPANIES_FILE = DATA_DIR / "companies.json"
FUNDAMENTALS_FILE = DATA_DIR / "fundamentals.json"


METRICS = [
    "market_cap",
    "roe_ttm",
    "roa_ttm",
    "pe_ttm",
    "pb_mrq",
    "forward_pe",
    "yield_ttm",
    "dividend_ttm",
    "yoy_quarter_revenue_growth",
    "yoy_quarter_earnings_growth"
]


def load_all_fundamentals(page_size=200):
    """
    Mengambil fundamentals seluruh universe
    menggunakan bulk request Sectors API v2.
    """

    try:
        universe = json.loads(COMPANIES_FILE.read_text(encoding="utf-8"))
    except Exception:
        universe = json.loads(FUNDAMENTALS_FILE.read_text(encoding="utf-8"))
    symbols = universe.keys() if isinstance(universe, dict) else (
        row.get("symbol") for row in universe if isinstance(row, dict)
    )
    records = []
    for number, symbol in enumerate((s for s in symbols if s), 1):
        print(f"Mengambil fundamentals Yahoo: {number} {symbol}")
        try:
            records.append(fundamental_record(symbol))
        except Exception as error:
            print(f"  ERROR: {error}")
    return records


def save_fundamentals(data):
    """
    Menyimpan fundamentals ke JSON lokal.
    """

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        FUNDAMENTALS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"\nData disimpan ke:"
    )

    print(
        FUNDAMENTALS_FILE
    )


def print_summary(data):
    """
    Menampilkan ringkasan kualitas data.
    """

    print("\n=== DATA QUALITY SUMMARY ===")

    print(
        f"Total perusahaan: {len(data)}"
    )

    print("\nCoverage:")

    for metric in METRICS:

        available = sum(
            1
            for company in data
            if company.get(metric) is not None
        )

        total = len(data)

        percentage = (
            available / total * 100
            if total
            else 0
        )

        print(
            f"{metric:35}"
            f"{available:4}/{total:<4}"
            f"({percentage:5.1f}%)"
        )


if __name__ == "__main__":

    print(
        "=== BAGGER RADAR FUNDAMENTAL INGESTION ==="
    )

    fundamentals = load_all_fundamentals()

    print_summary(
        fundamentals
    )

    save_fundamentals(
        fundamentals
    )
