#!/usr/bin/env python3
"""
Report players from the previously-invalid list that now have
regular-season logs in all_player_game_logs_regular_season.csv.
"""

from pathlib import Path
from typing import Dict, List

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
REG_SEASON_FILE = OUTPUT_DIR / "all_player_game_logs_regular_season.csv"
FILTERED_OUT_FILE = OUTPUT_DIR / "filtered_out_players.csv"


def read_target_players() -> pd.DataFrame:
    try:
        return pd.read_csv(DATA_DIR / "target_player.csv")
    except UnicodeDecodeError:
        return pd.read_csv(DATA_DIR / "target_player.csv", encoding="latin1")


def read_filtered_out() -> pd.DataFrame:
    return pd.read_csv(FILTERED_OUT_FILE)


def count_rows_for_ids(person_ids: List[int]) -> Dict[int, int]:
    counts: Dict[int, int] = {pid: 0 for pid in person_ids}
    if not REG_SEASON_FILE.exists() or not person_ids:
        return counts

    chunksize = 200_000
    for chunk in pd.read_csv(REG_SEASON_FILE, usecols=["person_id"], chunksize=chunksize):
        chunk_ids = chunk["person_id"].dropna().astype(int)
        matched = chunk_ids[chunk_ids.isin(person_ids)]
        if matched.empty:
            continue
        value_counts = matched.value_counts()
        for pid, cnt in value_counts.items():
            counts[int(pid)] += int(cnt)
    return counts


def main() -> None:
    if not FILTERED_OUT_FILE.exists():
        raise FileNotFoundError(f"Missing {FILTERED_OUT_FILE}")

    target = read_target_players()
    filtered = read_filtered_out()

    filtered_invalid = filtered[filtered["Reason"] == "invalid personId"].copy()
    filtered_names = set(filtered_invalid["Clean Name"].astype(str))

    target["personId"] = pd.to_numeric(target.get("personId"), errors="coerce")
    candidates = target[target["Clean Name"].astype(str).isin(filtered_names)]
    candidates = candidates[candidates["personId"].notna()].copy()

    person_ids = candidates["personId"].astype(int).unique().tolist()
    counts = count_rows_for_ids(person_ids)

    report_rows = []
    for _, row in candidates.iterrows():
        pid = int(row["personId"])
        row_count = counts.get(pid, 0)
        if row_count == 0:
            continue
        report_rows.append({
            "Player Name": row.get("Player Name"),
            "Clean Name": row.get("Clean Name"),
            "Birth Date": row.get("Birth Date"),
            "personId": pid,
            "Regular Season Rows": row_count,
        })

    report_df = pd.DataFrame(report_rows)
    report_path = OUTPUT_DIR / "appended_players_report.csv"
    report_df.to_csv(report_path, index=False)
    print(f"Saved report to: {report_path}")
    print(f"Players in report: {len(report_df)}")


if __name__ == "__main__":
    main()
