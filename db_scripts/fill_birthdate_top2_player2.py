#!/usr/bin/env python3
"""
Fill missing birthdate values in top2_games_per_season_player2.csv using
target_player2.csv column "Birth Date(TextToColumn)".
If still missing, set to "NA".
"""

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
TOP2_FILE = OUTPUT_DIR / "top2_games_per_season_player2.csv"
TARGET_FILE = DATA_DIR / "target_player2_with_personId.csv"
OUTPUT_FILE = OUTPUT_DIR / "top2_games_per_season_with_birthdate_player2.csv"


def read_target_players() -> pd.DataFrame:
    try:
        return pd.read_csv(TARGET_FILE)
    except UnicodeDecodeError:
        return pd.read_csv(TARGET_FILE, encoding="latin1")


def main() -> None:
    if not TOP2_FILE.exists():
        raise FileNotFoundError(f"Missing {TOP2_FILE}")

    top2 = pd.read_csv(TOP2_FILE, low_memory=False)
    if "birthdate" not in top2.columns:
        top2["birthdate"] = pd.NA

    target = read_target_players()
    target["personId"] = pd.to_numeric(target.get("personId"), errors="coerce")

    birth_col = "Birth Date(TextToColumn)"
    if birth_col not in target.columns:
        raise ValueError(f"Missing {birth_col} in target_player2.csv")
    target["birthdate_source"] = target[birth_col]

    birth_map = (
        target.dropna(subset=["personId"])
        .set_index("personId")["birthdate_source"]
        .to_dict()
    )

    top2["person_id"] = pd.to_numeric(top2.get("person_id"), errors="coerce")
    missing_mask = top2["birthdate"].isna() | (top2["birthdate"].astype(str).str.strip() == "")
    top2.loc[missing_mask, "birthdate"] = top2.loc[missing_mask, "person_id"].map(birth_map)

    still_missing = top2["birthdate"].isna() | (top2["birthdate"].astype(str).str.strip() == "")
    top2.loc[still_missing, "birthdate"] = "NA"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    top2.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
