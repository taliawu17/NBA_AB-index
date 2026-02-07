#!/usr/bin/env python3
"""
Select top 2 regular-season games per player per season by points.
Ties are broken by later gameDate (descending).
"""

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
REG_SEASON_FILE = OUTPUT_DIR / "all_player_game_logs_regular_season.csv"
ALL_LOGS_FILE = OUTPUT_DIR / "all_player_game_logs.csv"
OUTPUT_FILE = OUTPUT_DIR / "top2_games_per_season.csv"
PLAYERS_FILE = DATA_DIR / "Players.csv"
TARGET_FILE = DATA_DIR / "target_player.csv"
STATS_FILE = DATA_DIR / "PlayerStatistics.csv"


def main() -> None:
    df = None
    if REG_SEASON_FILE.exists():
        try:
            df = pd.read_csv(REG_SEASON_FILE, low_memory=False)
        except PermissionError:
            df = None

    if df is None:
        if not ALL_LOGS_FILE.exists():
            raise FileNotFoundError(f"Missing {REG_SEASON_FILE} and {ALL_LOGS_FILE}")
        df = pd.read_csv(ALL_LOGS_FILE, low_memory=False)
        df = df[df["gameType"] == "Regular Season"].copy()

    # Ensure any missing target personIds are included (e.g., appended after initial logs)
    try:
        target = pd.read_csv(TARGET_FILE)
    except UnicodeDecodeError:
        target = pd.read_csv(TARGET_FILE, encoding="latin1")

    target["personId"] = pd.to_numeric(target.get("personId"), errors="coerce")
    target = target[target["personId"].notna()]
    target_ids = set(target["personId"].astype(int))
    present_ids = set(df["person_id"].dropna().astype(int)) if "person_id" in df.columns else set()
    missing_ids = target_ids - present_ids

    if missing_ids:
        id_to_name = dict(
            zip(
                target["personId"].astype(int),
                target.get("Clean Name", target.get("Player Name")),
            )
        )
        chunksize = 200_000
        extra_rows = []
        for chunk in pd.read_csv(STATS_FILE, low_memory=False, chunksize=chunksize):
            chunk = chunk[chunk["personId"].isin(missing_ids)]
            chunk = chunk[chunk["gameType"] == "Regular Season"]
            if chunk.empty:
                continue
            chunk = chunk.copy()
            chunk["clean_name"] = chunk["personId"].map(id_to_name)
            chunk["person_id"] = chunk["personId"]
            chunk["year"] = pd.to_datetime(chunk["gameDate"]).dt.year
            extra_rows.append(chunk)
        if extra_rows:
            df = pd.concat([df] + extra_rows, ignore_index=True)
    if "gameDate" in df.columns:
        df["gameDate"] = pd.to_datetime(df["gameDate"], errors="coerce")
        df["gameDate2"] = (
            df["gameDate"].dt.day.astype("Int64").astype(str)
            + "/"
            + df["gameDate"].dt.month.astype("Int64").astype(str)
            + "/"
            + df["gameDate"].dt.year.astype("Int64").astype(str)
        )

    # Ensure required columns exist
    required_cols = {"person_id", "year", "points", "gameDate"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    # Attach birthdate from Players.csv (personId -> birthdate)
    if not PLAYERS_FILE.exists():
        raise FileNotFoundError(f"Missing {PLAYERS_FILE}")
    players = pd.read_csv(PLAYERS_FILE, usecols=["personId", "birthdate"])
    players["personId"] = pd.to_numeric(players["personId"], errors="coerce")
    birthdate_map = players.dropna(subset=["personId"]).set_index("personId")["birthdate"].to_dict()
    df["birthdate"] = df["person_id"].map(birthdate_map)

    # Sort by points desc, then gameDate desc
    df_sorted = df.sort_values(
        by=["person_id", "year", "points", "gameDate"],
        ascending=[True, True, False, False],
        kind="mergesort",
    )

    top2 = df_sorted.groupby(["person_id", "year"], sort=False).head(2)
    # Place birthdate column next to gameDate
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
