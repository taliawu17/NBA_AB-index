#!/usr/bin/env python3
"""
Build target_player2.csv from player_id_v3.csv with filters:
- retire age < 30
- career length >= 3
Check for duplicates within target_player2 and against target_player.csv.
"""

from pathlib import Path
import sys

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
SOURCE_FILE = DATA_DIR / "player_id_v3.csv"
TARGET_FILE = DATA_DIR / "target_player2.csv"
EXISTING_TARGET = DATA_DIR / "target_player.csv"


def main() -> None:
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(f"Missing {SOURCE_FILE}")

    df = pd.read_csv(SOURCE_FILE)
    required_cols = {"retire age", "career length"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    filtered = df[
        (pd.to_numeric(df["retire age"], errors="coerce") < 30)
        & (pd.to_numeric(df["career length"], errors="coerce") >= 3)
    ].copy()

    # Keep duplicates; player_id can distinguish them

    # Duplicate check against existing target_player.csv (by Player Name or Clean Name)
    if EXISTING_TARGET.exists():
        try:
            existing = pd.read_csv(EXISTING_TARGET)
        except UnicodeDecodeError:
            existing = pd.read_csv(EXISTING_TARGET, encoding="latin1")

        if "Player Name" in filtered.columns and "Player Name" in existing.columns:
            overlap = set(filtered["Player Name"]) & set(existing["Player Name"])
        elif "Clean Name" in filtered.columns and "Clean Name" in existing.columns:
            overlap = set(filtered["Clean Name"]) & set(existing["Clean Name"])
        else:
            overlap = set()

        if overlap:
            print(f"Duplicates found against target_player.csv: {sorted(overlap)}")

    # Ensure required identifiers are present in output
    if "player_id" not in filtered.columns:
        raise ValueError("Missing required column: player_id")
    if "Birth Date" not in filtered.columns:
        raise ValueError("Missing required column: Birth Date")

    filtered.to_csv(TARGET_FILE, index=False)
    print(f"Saved {len(filtered)} players to {TARGET_FILE}")


if __name__ == "__main__":
    main()
