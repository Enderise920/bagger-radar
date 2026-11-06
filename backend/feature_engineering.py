import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

QUALITY_FILE = DATA_DIR / "fundamentals_quality.json"


def load_quality_data():
    """
    Membaca dataset yang sudah diperkaya
    dengan data quality.
    """

    with open(
        QUALITY_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def safe_value(value):
    """
    Mengubah nilai None menjadi None
    dan memastikan angka tetap numerik.
    """

    if value is None:
        return None

    try:
        return float(value)

    except (TypeError, ValueError):
        return None


def build_features(company):
    """
    Membuat feature set untuk satu perusahaan.
    """

    revenue_growth = safe_value(
        company.get(
            "yoy_quarter_revenue_growth"
        )
    )

    earnings_growth = safe_value(
        company.get(
            "yoy_quarter_earnings_growth"
        )
    )

    roe = safe_value(
        company.get("roe_ttm")
    )

    roa = safe_value(
        company.get("roa_ttm")
    )

    pe = safe_value(
        company.get("pe_ttm")
    )

    pb = safe_value(
        company.get("pb_mrq")
    )

    # PE hanya valid jika > 0
    valid_pe = (
        pe is not None
        and pe > 0
    )

    # PB hanya valid jika > 0
    valid_pb = (
        pb is not None
        and pb > 0
    )

    features = {
        "symbol": company.get("symbol"),
        "company_name": company.get(
            "company_name"
        ),

        "data_confidence": company.get(
            "data_confidence"
        ),

        # Growth
        "growth": {
            "revenue_growth": revenue_growth,
            "earnings_growth": earnings_growth
        },

        # Quality
        "quality": {
            "roe": roe,
            "roa": roa
        },

        # Valuation
        "valuation": {
            "pe": pe if valid_pe else None,
            "pb": pb if valid_pb else None,
            "pe_valid": valid_pe,
            "pb_valid": valid_pb
        }
    }

    return features


def build_feature_dataset(data):
    """
    Membuat feature dataset untuk seluruh perusahaan.
    """

    features = []

    for company in data:

        feature = build_features(
            company
        )

        features.append(feature)

    return features


def print_summary(features):
    """
    Menampilkan ringkasan feature coverage.
    """

    total = len(features)

    revenue_growth = sum(
        1
        for company in features
        if company["growth"]["revenue_growth"]
        is not None
    )

    earnings_growth = sum(
        1
        for company in features
        if company["growth"]["earnings_growth"]
        is not None
    )

    roe = sum(
        1
        for company in features
        if company["quality"]["roe"]
        is not None
    )

    roa = sum(
        1
        for company in features
        if company["quality"]["roa"]
        is not None
    )

    pe = sum(
        1
        for company in features
        if company["valuation"]["pe"]
        is not None
    )

    pb = sum(
        1
        for company in features
        if company["valuation"]["pb"]
        is not None
    )

    print(
        "\n=== FEATURE COVERAGE ==="
    )

    print(
        f"Revenue Growth : "
        f"{revenue_growth}/{total}"
    )

    print(
        f"Earnings Growth: "
        f"{earnings_growth}/{total}"
    )

    print(
        f"ROE            : "
        f"{roe}/{total}"
    )

    print(
        f"ROA            : "
        f"{roa}/{total}"
    )

    print(
        f"Valid PE       : "
        f"{pe}/{total}"
    )

    print(
        f"Valid PB       : "
        f"{pb}/{total}"
    )


if __name__ == "__main__":

    print(
        "=== BAGGER RADAR FEATURE ENGINEERING ==="
    )

    data = load_quality_data()

    features = build_feature_dataset(
        data
    )

    print_summary(
        features
    )

    print(
        "\n=== SAMPLE FEATURES ==="
    )

    for company in features[:10]:

        print(
            company["symbol"],
            "|",
            company["data_confidence"],
            "|",
            company["growth"],
            "|",
            company["quality"],
            "|",
            company["valuation"]
        )