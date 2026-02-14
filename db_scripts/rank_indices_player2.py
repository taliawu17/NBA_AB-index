#!/usr/bin/env python3
"""
Rank player2_index.csv by:
index desc, pts desc, age_years desc, age_days desc.
"""

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "output"
INPUT_FILE = OUTPUT_DIR / "player2_index.csv"
OUTPUT_FILE = OUTPUT_DIR / "player2_index_ranked.csv"


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Missing {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)
    if "index" not in df.columns:
        raise ValueError("Missing index column in player2_index.csv")

    ranked = df.copy()
    ranked = ranked[ranked["index"] != "NA"].copy()
    ranked["index"] = pd.to_numeric(ranked["index"], errors="coerce")
    ranked["pts"] = pd.to_numeric(ranked.get("pts"), errors="coerce")
    ranked["age_years"] = pd.to_numeric(ranked.get("age_years"), errors="coerce")
    ranked["age_days"] = pd.to_numeric(ranked.get("age_days"), errors="coerce")

    ranked = ranked.sort_values(
        ["index", "pts", "age_years", "age_days"],
        ascending=[False, False, False, False],
        kind="mergesort",
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ranked.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved ranked file: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
