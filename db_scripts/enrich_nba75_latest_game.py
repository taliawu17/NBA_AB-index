#!/usr/bin/env python3
"""
Enrich nba75_rankings.csv with AB-index and age at latest key-log game.

Reads:
  nba75_rankings.csv (column Player Name)
  output/player{1,2,3}_key_game_logs_age.csv
  output/player_index_all.csv

Writes:
  nba75_latestGame.csv (repo root)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "output"
NBA75_IN = BASE_DIR / "nba75_rankings.csv"
NBA75_OUT = BASE_DIR / "nba75_latestGame.csv"

KEY_LOG_PATHS = (
    OUTPUT_DIR / "player1_key_game_logs_age.csv",
    OUTPUT_DIR / "player2_key_game_logs_age.csv",
    OUTPUT_DIR / "player3_key_game_logs_age.csv",
)
INDEX_PATH = OUTPUT_DIR / "player_index_all.csv"

# NBA 75 display name -> name in key logs / index (clean_name / player_name)
NBA75_NAME_ALIASES: dict[str, str] = {
    "Nate Archibald": "Tiny Archibald",
}


def log_name_for_nba75(player_name: str) -> str:
    return NBA75_NAME_ALIASES.get(player_name.strip(), player_name.strip())


def load_key_logs() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in KEY_LOG_PATHS:
        if not path.is_file():
            raise FileNotFoundError(path)
        df = pd.read_csv(path, low_memory=False)
        if "gameDate" not in df.columns and "gameDateTimeEst" in df.columns:
            df["gameDate"] = df["gameDateTimeEst"]
        need = ["clean_name", "gameDate", "age_years", "age_days", "age_at_game"]
        missing = set(need) - set(df.columns)
        if missing:
            raise ValueError(f"{path.name} missing columns: {sorted(missing)}")
        frames.append(df[need + (["personId"] if "personId" in df.columns else [])])
    out = pd.concat(frames, ignore_index=True)
    out["clean_name"] = out["clean_name"].astype(str).str.strip()
    out["gameDate"] = pd.to_datetime(out["gameDate"], dayfirst=True, errors="coerce")
    return out


def last_game_ages(logs: pd.DataFrame) -> pd.DataFrame:
    work = logs.dropna(subset=["gameDate"]).sort_values(
        ["clean_name", "gameDate"], ascending=[True, True], kind="mergesort"
    )
    last = work.groupby("clean_name", as_index=False).tail(1)
    cols = {
        "clean_name": "log_player_name",
        "gameDate": "last_game_date",
        "age_years": "age_years_last_game",
        "age_days": "age_days_last_game",
        "age_at_game": "age_at_last_game",
    }
    out = last.rename(columns=cols)[[c for c in cols.values()]]
    if "personId" in last.columns:
        out.insert(1, "personId", last["personId"].values)
    return out


def load_ab_index() -> pd.DataFrame:
    idx = pd.read_csv(INDEX_PATH, low_memory=False)
    idx["player_name"] = idx["player_name"].astype(str).str.strip()
    keep = ["player_name", "index", "AB_rank"]
    keep = [c for c in keep if c in idx.columns]
    return idx[keep].rename(
        columns={"player_name": "log_player_name", "index": "AB_index"}
    )


def main() -> None:
    if not NBA75_IN.is_file():
        raise FileNotFoundError(NBA75_IN)
    if not INDEX_PATH.is_file():
        raise FileNotFoundError(f"Run combine_player_indices.py first: {INDEX_PATH}")

    nba75 = pd.read_csv(NBA75_IN)
    if "Player Name" not in nba75.columns:
        raise ValueError("nba75_rankings.csv must contain column 'Player Name'")
    nba75["Player Name"] = nba75["Player Name"].astype(str).str.strip()
    nba75["log_player_name"] = nba75["Player Name"].map(log_name_for_nba75)

    last = last_game_ages(load_key_logs())
    ab = load_ab_index()

    out = nba75.merge(last, on="log_player_name", how="left")
    out = out.merge(ab, on="log_player_name", how="left", suffixes=("", "_ab"))
    out = out.drop(columns=["log_player_name"])

    out.to_csv(NBA75_OUT, index=False)
    n = len(nba75)
    has_last = out["age_years_last_game"].notna().sum()
    has_ab = pd.to_numeric(out["AB_index"], errors="coerce").notna().sum()
    print(f"Saved: {NBA75_OUT}")
    print(f"  rows: {n}")
    print(f"  with last-game age: {has_last}")
    print(f"  with AB_index: {has_ab}")
    missing = out.loc[out["age_years_last_game"].isna(), "Player Name"].tolist()
    if missing:
        print(f"  no key-log match: {missing}")


if __name__ == "__main__":
    main()
