import json
from pathlib import Path
from datetime import datetime, timezone

OUTPUT_FILE = Path("data/company_profiles.json")

TEST_PROFILE = {
    "symbol": "AADI.JK",
    "company_name": "PT Adaro Andalan Indonesia Tbk",
    "description": (
        "Perusahaan energi terintegrasi yang bergerak di bidang "
        "pertambangan batubara dan layanan pendukungnya, termasuk "
        "jasa pertambangan, logistik, dan pengembangan energi."
    ),
    "sector": "Energy",
    "industry": "Oil, Gas & Coal",
    "source": "IDX / Adaro company profile",
    "source_url": "https://rdis.idx.co.id/en/events/profil-emiten-saham-aadi",
    "retrieved_at": datetime.now(timezone.utc).isoformat(),
}


def update_profile():
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        profiles = json.load(f)

    updated = False

    for profile in profiles:
        if profile["symbol"] == "AADI.JK":
            profile.update(TEST_PROFILE)
            updated = True
            break

    if not updated:
        raise ValueError("AADI.JK tidak ditemukan")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

    print("AADI.JK profile updated successfully.")
    print(json.dumps(TEST_PROFILE, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    update_profile()