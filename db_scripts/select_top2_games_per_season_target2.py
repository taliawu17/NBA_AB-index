#!/usr/bin/env python3
"""
Select top 2 regular-season games per player per season by points.
Ties are broken by later gameDate (descending).
Uses all_player2_game_logs.csv as input.
"""

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
ALL_LOGS_FILE = OUTPUT_DIR / "all_player2_game_logs.csv"
OUTPUT_FILE = OUTPUT_DIR / "top2_games_per_season_player2.csv"
PLAYERS_FILE = DATA_DIR / "Players.csv"


def main() -> None:
    if not ALL_LOGS_FILE.exists():
        raise FileNotFoundError(f"Missing {ALL_LOGS_FILE}")

    df = pd.read_csv(ALL_LOGS_FILE, low_memory=False)
    df = df[df["gameType"] == "Regular Season"].copy()

    if "gameDate" in df.columns:
        df["gameDate"] = pd.to_datetime(df["gameDate"], errors="coerce")
        df["gameDate2"] = (
            df["gameDate"].dt.day.astype("Int64").astype(str)
            + "/"
            + df["gameDate"].dt.month.astype("Int64").astype(str)
            + "/"
            + df["gameDate"].dt.year.astype("Int64").astype(str)
        )

    required_cols = {"person_id", "year", "points", "gameDate"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    if not PLAYERS_FILE.exists():
        raise FileNotFoundError(f"Missing {PLAYERS_FILE}")
    players = pd.read_csv(PLAYERS_FILE, usecols=["personId", "birthdate"])
    players["personId"] = pd.to_numeric(players["personId"], errors="coerce")
    birthdate_map = players.dropna(subset=["personId"]).set_index("personId")["birthdate"].to_dict()
    df["birthdate"] = df["person_id"].map(birthdate_map)

    df_sorted = df.sort_values(
        by=["person_id", "year", "points", "gameDate"],
        ascending=[True, True, False, False],
        kind="mergesort",
    )
    top2 = df_sorted.groupby(["person_id", "year"], sort=False).head(2)

    columns = top2.columns.tolist()
    if "gameDate" in columns and "gameDate2" in columns:
        columns.remove("gameDate2")
        game_date_idx = columns.index("gameDate") + 1
        columns.insert(game_date_idx, "gameDate2")
    if "gameDate" in columns and "birthdate" in columns:
        columns.remove("birthdate")
        game_date_idx = columns.index("gameDate") + 1
        if "gameDate2" in columns:
            game_date_idx += 1
        columns.insert(game_date_idx, "birthdate")
    top2 = top2[columns]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    top2.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved top 2 games per season to: {OUTPUT_FILE}")
    print(f"Total rows: {len(top2)}")


if __name__ == "__main__":
    main()
