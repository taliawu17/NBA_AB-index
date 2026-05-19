#!/usr/bin/env python3
"""
Add BeforeAfter2014 to output/player_index_ranked_all.csv.

Uses player1/2/3_key_game_logs.csv (season `year` = season end year).
BeforeAfter2014 = 1 if the player has games with year <= 2014 AND year >= 2015
(i.e. played before the 2014-15 season and in 2014-15 or later); else 0.

Re-run after updating key logs or ranked index:
  python db_scripts/combine_player_indices.py
  python db_scripts/add_before_after_2014.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "output"
RANKED_PATH = OUTPUT_DIR / "player_index_ranked_all.csv"

KEY_LOG_PATHS = (
    OUTPUT_DIR / "player1_key_game_logs.csv",
    OUTPUT_DIR / "player2_key_game_logs.csv",
    OUTPUT_DIR / "player3_key_game_logs.csv",
)

BEFORE_YEAR_MAX = 2014
AFTER_YEAR_MIN = 2015


def load_key_logs() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in KEY_LOG_PATHS:
        if not path.is_file():
            raise FileNotFoundError(path)
        df = pd.read_csv(path, usecols=["personId", "year"], low_memory=False)
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out["personId"] = pd.to_numeric(out["personId"], errors="coerce")
    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    return out.dropna(subset=["personId", "year"])


def before_after_2014_flags(logs: pd.DataFrame) -> pd.DataFrame:
    def flags_for_player(years: pd.Series) -> int:
        ys = set(years.astype(int))
        has_before = any(y <= BEFORE_YEAR_MAX for y in ys)
        has_after = any(y >= AFTER_YEAR_MIN for y in ys)
        return int(has_before and has_after)

    flags = (
        logs.groupby("personId", sort=False)["year"]
        .apply(flags_for_player)
        .rename("BeforeAfter2014")
        .reset_index()
    )
    flags["BeforeAfter2014"] = flags["BeforeAfter2014"].astype(int)
    return flags


def main() -> None:
    if not RANKED_PATH.is_file():
        raise FileNotFoundError(f"Missing {RANKED_PATH}")

    ranked = pd.read_csv(RANKED_PATH, low_memory=False)
    ranked["personId"] = pd.to_numeric(ranked["personId"], errors="coerce")

    # drop stray empty columns from Excel round-trips
    ranked = ranked.loc[:, ~ranked.columns.str.match(r"^Unnamed")]

    flags = before_after_2014_flags(load_key_logs())
    if "BeforeAfter2014" in ranked.columns:
        ranked = ranked.drop(columns=["BeforeAfter2014"])

    out = ranked.merge(flags, on="personId", how="left")
    out["BeforeAfter2014"] = out["BeforeAfter2014"].fillna(0).astype(int)

    out.to_csv(RANKED_PATH, index=False)
    n1 = int(out["BeforeAfter2014"].sum())
    print(f"Saved: {RANKED_PATH}")
    print(f"  rows: {len(out):,}")
    print(f"  BeforeAfter2014 = 1: {n1:,}")
    print(f"  BeforeAfter2014 = 0: {len(out) - n1:,}")


if __name__ == "__main__":
    main()
