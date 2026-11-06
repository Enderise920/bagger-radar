import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

FUNDAMENTALS_FILE = DATA_DIR / "fundamentals.json"


CORE_METRICS = [
    "roe_ttm",
    "roa_ttm",
    "pe_ttm",
    "pb_mrq",
    "yoy_quarter_revenue_growth",
    "yoy_quarter_earnings_growth"
]


def load_fundamentals():
    """
    Membaca fundamentals dari JSON lokal.
    """

    with open(
        FUNDAMENTALS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def calculate_quality(company):
    """
    Menghitung data quality untuk satu perusahaan.
    """

    missing_metrics = []

    available_metrics = 0

    for metric in CORE_METRICS:

        value = company.get(metric)

        if value is None:

            missing_metrics.append(metric)

        else:

            available_metrics += 1

    total_metrics = len(CORE_METRICS)

    completeness = (
        available_metrics / total_metrics
        if total_metrics
        else 0
    )

    pe = company.get("pe_ttm")
    pb = company.get("pb_mrq")

    invalid_pe = (
        pe is not None
        and pe <= 0
    )

    invalid_pb = (
        pb is not None
        and pb <= 0
    )

    return {
        "available_core_metrics": available_metrics,
        "missing_core_metrics": missing_metrics,
        "core_completeness": completeness,
        "invalid_pe": invalid_pe,
        "invalid_pb": invalid_pb
    }


def confidence_label(completeness):
    """
    Memberikan label confidence berdasarkan
    kelengkapan data core metrics.
    """

    if completeness >= 0.80:

        return "HIGH"

    if completeness >= 0.50:

        return "MEDIUM"

    return "LOW"


def analyze_dataset(data):
    """
    Menganalisis seluruh dataset.
    """

    total = len(data)

    high = 0
    medium = 0
    low = 0

    invalid_pe_count = 0
    invalid_pb_count = 0

    enriched = []

    for company in data:

        quality = calculate_quality(
            company
        )

        label = confidence_label(
            quality["core_completeness"]
        )

        if label == "HIGH":
            high += 1

        elif label == "MEDIUM":
            medium += 1

        else:
            low += 1

        if quality["invalid_pe"]:
            invalid_pe_count += 1

        if quality["invalid_pb"]:
            invalid_pb_count += 1

        enriched_company = {
            **company,
            "data_quality": quality,
            "data_confidence": label
        }

        enriched.append(
            enriched_company
        )

    return {
        "total": total,
        "high": high,
        "medium": medium,
        "low": low,
        "invalid_pe": invalid_pe_count,
        "invalid_pb": invalid_pb_count,
        "data": enriched
    }


if __name__ == "__main__":

    print(
        "=== BAGGER RADAR DATA QUALITY ==="
    )

    data = load_fundamentals()

    analysis = analyze_dataset(
        data
    )

    print(
        f"\nTotal perusahaan: "
        f"{analysis['total']}"
    )

    print(
        f"HIGH confidence: "
        f"{analysis['high']}"
    )

    print(
        f"MEDIUM confidence: "
        f"{analysis['medium']}"
    )

    print(
        f"LOW confidence: "
        f"{analysis['low']}"
    )

    print(
        f"\nInvalid PE: "
        f"{analysis['invalid_pe']}"
    )

    print(
        f"Invalid PB: "
        f"{analysis['invalid_pb']}"
    )

    print("\n=== SAMPLE ===")

    for company in analysis["data"][:10]:

        print(
            company["symbol"],
            "|",
            company["data_confidence"],
            "|",
            company["data_quality"]
        )