import json
from pathlib import Path

from data_quality import (
    load_fundamentals,
    analyze_dataset
)


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

QUALITY_FILE = DATA_DIR / "fundamentals_quality.json"


def save_quality_data(data):
    """
    Menyimpan dataset yang sudah diperkaya
    dengan data quality dan confidence.
    """

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        QUALITY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("\nData quality disimpan ke:")
    print(QUALITY_FILE)


def print_quality_report(analysis):
    """
    Menampilkan ringkasan data quality.
    """

    total = analysis["total"]

    print("\n=== BAGGER RADAR DATA QUALITY REPORT ===")

    print(
        f"Total perusahaan : {total}"
    )

    print(
        f"HIGH             : "
        f"{analysis['high']} "
        f"({analysis['high'] / total * 100:.1f}%)"
    )

    print(
        f"MEDIUM           : "
        f"{analysis['medium']} "
        f"({analysis['medium'] / total * 100:.1f}%)"
    )

    print(
        f"LOW              : "
        f"{analysis['low']} "
        f"({analysis['low'] / total * 100:.1f}%)"
    )

    print(
        f"\nInvalid PE       : "
        f"{analysis['invalid_pe']}"
    )

    print(
        f"Invalid PB       : "
        f"{analysis['invalid_pb']}"
    )


def print_examples(data):
    """
    Menampilkan contoh perusahaan
    dengan berbagai kondisi data.
    """

    print("\n=== EXAMPLES ===")

    examples = []

    for company in data:

        if company["data_confidence"] == "HIGH":
            examples.append(company)

        if len(examples) >= 3:
            break

    for company in examples:

        quality = company["data_quality"]

        print(
            f"{company['symbol']} | "
            f"{company['data_confidence']} | "
            f"completeness="
            f"{quality['core_completeness']:.2%} | "
            f"invalid_pe="
            f"{quality['invalid_pe']} | "
            f"invalid_pb="
            f"{quality['invalid_pb']}"
        )


if __name__ == "__main__":

    print(
        "=== BAGGER RADAR QUALITY PIPELINE ==="
    )

    fundamentals = load_fundamentals()

    analysis = analyze_dataset(
        fundamentals
    )

    print_quality_report(
        analysis
    )

    print_examples(
        analysis["data"]
    )

    save_quality_data(
        analysis["data"]
    )