#!/usr/bin/env python3
"""
Union table: NBA75 OR Basketball 100 OR AB-index >= 33.

Output format matches legacy 3rankings.csv:
  Player Name, player_id, NBA75_rank, V_index, V_ranking, B100_Rank

Inputs:
  nba75_rankings.csv
  basketball100.csv
  output/player_index_ranked_all.csv  (AB-index >= 33)

Default output: 3rankings_20260518.csv (repo root)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
NBA75_PATH = BASE_DIR / "nba75_rankings.csv"
B100_PATH = BASE_DIR / "basketball100.csv"
AB_RANKED_PATH = BASE_DIR / "output" / "player_index_ranked_all.csv"
PLAYER_ID_PATH = BASE_DIR / "data" / "player_id_v3.csv"
DEFAULT_OUT = BASE_DIR / "3rankings_20260518.csv"

# Alternate name in source data -> canonical Player Name for union row
NAME_ALIASES: dict[str, str] = {
    "Tiny Archibald": "Nate Archibald",
    "Penny Hardaway": "Anfernee Hardaway",
    "Tim Hardaway Sr.": "Tim Hardaway",
    "Mel Daniels*": "Mel Daniels",
}


def canonical_name(name: str) -> str:
    s = str(name).strip()
    return NAME_ALIASES.get(s, s)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build 3rankings union CSV")
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--min-index", type=int, default=33)
    args = parser.parse_args()

    nba75 = pd.read_csv(NBA75_PATH)
    nba75["NBA75_rank"] = pd.to_numeric(nba75["NBA75_rank"], errors="coerce")
    nba75 = nba75.dropna(subset=["Player Name"])
    nba75["canonical_name"] = nba75["Player Name"].map(canonical_name)
    nba75 = nba75[nba75["NBA75_rank"].between(1, 76, inclusive="both")]
    nba75_names = set(nba75["canonical_name"])

    b100 = pd.read_csv(B100_PATH)
    b100["B100_Rank"] = pd.to_numeric(b100["B100_Rank"], errors="coerce")
    b100 = b100.dropna(subset=["Player Name"])
    b100["canonical_name"] = b100["Player Name"].map(canonical_name)
    b100_names = set(b100["canonical_name"])

    ab = pd.read_csv(AB_RANKED_PATH, low_memory=False)
    ab["index"] = pd.to_numeric(ab["index"], errors="coerce")
    ab = ab.dropna(subset=["player_name", "index"])
    ab = ab[ab["index"] >= args.min_index]
    ab["canonical_name"] = ab["player_name"].map(canonical_name)
    ab_names = set(ab["canonical_name"])

    union_names = sorted(nba75_names | b100_names | ab_names)
    out = pd.DataFrame({"Player Name": union_names})

    nba75_sub = (
        nba75[["canonical_name", "NBA75_rank"]]
        .drop_duplicates(subset=["canonical_name"], keep="first")
        .rename(columns={"canonical_name": "Player Name"})
    )
    out = out.merge(nba75_sub, on="Player Name", how="left")

    b100_sub = (
        b100[["canonical_name", "B100_Rank"]]
        .drop_duplicates(subset=["canonical_name"], keep="first")
        .rename(columns={"canonical_name": "Player Name"})
    )
    out = out.merge(b100_sub, on="Player Name", how="left")

    ab_sub = (
        ab[["canonical_name", "index", "AB_rank"]]
        .drop_duplicates(subset=["canonical_name"], keep="first")
        .rename(
            columns={
                "canonical_name": "Player Name",
                "index": "V_index",
                "AB_rank": "V_ranking",
            }
        )
    )
    out = out.merge(ab_sub, on="Player Name", how="left")

    if PLAYER_ID_PATH.is_file():
        pid = pd.read_csv(PLAYER_ID_PATH)
        clean_col = "Clean Name" if "Clean Name" in pid.columns else "Player Name"
        pid["canonical_name"] = pid[clean_col].map(canonical_name)
        pid_sub = (
            pid[["canonical_name", "player_id"]]
            .dropna(subset=["canonical_name"])
            .drop_duplicates(subset=["canonical_name"], keep="first")
            .rename(columns={"canonical_name": "Player Name"})
        )
        out = out.merge(pid_sub, on="Player Name", how="left")

    cols = ["Player Name", "player_id", "NBA75_rank", "V_index", "V_ranking", "B100_Rank"]
    out = out[[c for c in cols if c in out.columns]]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)

    print(f"NBA75: {len(nba75_names)}")
    print(f"B100: {len(b100_names)}")
    print(f"AB-index >= {args.min_index}: {len(ab_names)}")
    print(f"Union rows: {len(out)}")
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
