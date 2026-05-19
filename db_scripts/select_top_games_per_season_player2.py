#!/usr/bin/env python3
"""
Batch 2: top 2 + witness games (scheme 1).

Input:  output/player2_key_game_logs_age.csv  (age_years from Excel)
Output: output/top_games_per_season_player2.csv
"""

from pathlib import Path

import pandas as pd

from top_games_selection import (
    prepare_key_logs_for_top_games_selection,
    reorder_birthdate_columns,
    select_top2_plus_witness,
)

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "output"
KEY_LOGS_FILE = OUTPUT_DIR / "player2_key_game_logs_age.csv"
OUTPUT_FILE = OUTPUT_DIR / "top_games_per_season_player2.csv"


def main() -> None:
    if not KEY_LOGS_FILE.is_file():
        raise FileNotFoundError(f"Missing {KEY_LOGS_FILE}")

    df = pd.read_csv(KEY_LOGS_FILE, low_memory=False)
    n_in = len(df)

    work = prepare_key_logs_for_top_games_selection(df)
    selected = select_top2_plus_witness(work, top_n=2)
    selected = reorder_birthdate_columns(selected)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    selected.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved: {OUTPUT_FILE}")
    print(f"Total rows: {len(selected):,} (from {n_in:,} key-log games)")


if __name__ == "__main__":
    main()
