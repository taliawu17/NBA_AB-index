#!/usr/bin/env python3
"""
Rank batch-3 AB-index results (valid indices only).

Input:  output/player3_index.csv  (from calculate_indices_player3.py)
Output: output/player3_index_ranked.csv

Run order: 6) after calculate_indices_player3.py.
Tie-break: index, pts, age_years, age_days (all descending), matching paper wording.
"""

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "output"
INPUT_FILE = OUTPUT_DIR / "player3_index.csv"
OUTPUT_FILE = OUTPUT_DIR / "player3_index_ranked.csv"


def _save_ranked_csv(df: pd.DataFrame, out: Path) -> Path:
    try:
        df.to_csv(out, index=False)
        return out
    except PermissionError:
        alt = out.parent / f"{out.stem}_new{out.suffix}"
        df.to_csv(alt, index=False)
        print(
            f"Permission denied for {out} (file may be open elsewhere). "
            f"Wrote: {alt}"
        )
        return alt


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Missing {INPUT_FILE}. Run calculate_indices_player3.py first.")

    df = pd.read_csv(INPUT_FILE, low_memory=False)
    idx_num = pd.to_numeric(df["index"], errors="coerce")
    valid = df.loc[idx_num.notna()].copy()
    if valid.empty:
        print("No valid (non-NA) indices to rank; writing empty ranked file.")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = _save_ranked_csv(valid, OUTPUT_FILE)
        print(f"Saved: {path} ({len(valid)} rows)")
        return

    valid["index"] = idx_num.loc[valid.index].astype(int)
    valid = valid.loc[valid["index"] >= 18].copy()
    if valid.empty:
        print("No indices >= 18 to rank; writing empty ranked file.")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = _save_ranked_csv(valid, OUTPUT_FILE)
        print(f"Saved: {path} ({len(valid)} rows)")
        return
    valid["age_years"] = pd.to_numeric(valid["age_years"], errors="coerce")
    valid["age_days"] = pd.to_numeric(valid["age_days"], errors="coerce")
    valid["pts"] = pd.to_numeric(valid["pts"], errors="coerce")
    ranked = valid.sort_values(
        ["index", "pts", "age_years", "age_days"],
        ascending=[False, False, False, False],
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = _save_ranked_csv(ranked, OUTPUT_FILE)
    print(f"Saved: {path} ({len(ranked)} rows)")


if __name__ == "__main__":
    main()
