#!/usr/bin/env python3
"""
Extract key columns from batch-1 regular-season logs, add birthdate,
and trim gameDate to date-only.
"""

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
FALLBACK_DATA_DIR = BASE_DIR.parent / "data"

OUTPUT_DIR = BASE_DIR / "output"
FALLBACK_OUTPUT_DIR = BASE_DIR.parent / "output"

TARGET_PLAYERS_FILE = DATA_DIR / "target_player_with_personId.csv"
if not TARGET_PLAYERS_FILE.exists():
    TARGET_PLAYERS_FILE = FALLBACK_DATA_DIR / "target_player_with_personId.csv"

GAME_LOGS_FILE = OUTPUT_DIR / "all_player_game_logs_regular_season.csv"
if not GAME_LOGS_FILE.exists():
    GAME_LOGS_FILE = FALLBACK_OUTPUT_DIR / "all_player_game_logs_regular_season.csv"
OUTPUT_FILE = GAME_LOGS_FILE.parent / "player1_key_game_logs.csv"


def main() -> None:
    if not GAME_LOGS_FILE.exists():
        raise FileNotFoundError(f"Missing {GAME_LOGS_FILE}")
    if not TARGET_PLAYERS_FILE.exists():
        raise FileNotFoundError(f"Missing {TARGET_PLAYERS_FILE}")

    usecols_logs = [
        "firstName",
        "lastName",
        "clean_name",
        "year",
        "personId",
        "gameId",
        "gameDate",
        "points",
    ]
    logs = pd.read_csv(GAME_LOGS_FILE, usecols=usecols_logs, low_memory=False)

    logs["gameDate2"] = pd.to_datetime(logs["gameDate"], errors="coerce").dt.date

    target_cols = ["personId", "Birth Date(TextToColumn)"]
    target = pd.read_csv(TARGET_PLAYERS_FILE, usecols=target_cols)

    logs["personId"] = pd.to_numeric(logs["personId"], errors="coerce")
    target["personId"] = pd.to_numeric(target["personId"], errors="coerce")

    merged = logs.merge(
        target.rename(columns={"Birth Date(TextToColumn)": "birth_date"}),
        on="personId",
        how="left",
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
