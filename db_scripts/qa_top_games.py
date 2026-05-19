#!/usr/bin/env python3
"""Quality checks for top_games_per_season_player*.csv outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _norm_birth(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    if s.lower() in ("nan", "nat", "none", "na"):
        return ""
    return s


def check_file(path: Path) -> dict:
    df = pd.read_csv(path, low_memory=False)
    name = path.name

    empty_gd = df["gameDate"].isna() if "gameDate" in df.columns else pd.Series(dtype=bool)
    if "gameDate" in df.columns:
        empty_gd = empty_gd | (df["gameDate"].astype(str).str.strip() == "")

    out: dict = {
        "file": name,
        "rows": len(df),
        "gameDate_empty": int(empty_gd.sum()),
        "gameDate2_filled_when_empty": 0,
        "birth_mismatch_players": 0,
    }

    if out["gameDate_empty"] and "gameDate2" in df.columns:
        sub = df.loc[empty_gd, "gameDate2"]
        out["gameDate2_filled_when_empty"] = int(sub.notna().sum())

    if "birthdate" in df.columns and "birth_date" in df.columns:
        id_col = "personId" if "personId" in df.columns else "person_id"
        name_col = "clean_name" if "clean_name" in df.columns else "player_name"
        per = (
            df.groupby([id_col, name_col], dropna=False)
            .agg(b1=("birthdate", "first"), b2=("birth_date", "first"))
            .reset_index()
        )
        per["_b1"] = per["b1"].map(_norm_birth)
        per["_b2"] = per["b2"].map(_norm_birth)
        diff = per[(per["_b1"] != per["_b2"]) & ~((per["_b1"] == "") & (per["_b2"] == ""))]
        out["birth_mismatch_players"] = len(diff)
        if len(diff):
            mismatch_path = path.parent / f"qa_birthdate_mismatch_{path.stem}.csv"
            diff[[id_col, name_col, "b1", "b2"]].rename(
                columns={"b1": "birthdate", "b2": "birth_date"}
            ).to_csv(mismatch_path, index=False)
            out["birth_mismatch_csv"] = str(mismatch_path)

    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="QA top_games_per_season CSVs")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "output",
    )
    args = parser.parse_args()
    out_dir = args.output_dir

    for pattern in ("top_games_per_season_player1.csv", "top_games_per_season_player2.csv"):
        path = out_dir / pattern
        if not path.is_file():
            print(f"SKIP (missing): {path}")
            continue
        r = check_file(path)
        print(f"\n=== {r['file']} ===")
        print(f"  rows: {r['rows']:,}")
        print(f"  gameDate empty: {r['gameDate_empty']:,}")
        if r["gameDate_empty"]:
            print(f"  gameDate2 present when gameDate empty: {r['gameDate2_filled_when_empty']:,}")
        print(f"  players birthdate != birth_date: {r['birth_mismatch_players']}")
        if r.get("birth_mismatch_csv"):
            print(f"  wrote: {r['birth_mismatch_csv']}")


if __name__ == "__main__":
    main()
