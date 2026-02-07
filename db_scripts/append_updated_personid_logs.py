#!/usr/bin/env python3
"""
Append regular-season game logs for players whose personId was updated manually.

Source of candidates:
- output/filtered_out_players.csv with Reason == "invalid personId"
We re-check target_player.csv for updated personId values and append logs if missing.
"""

from pathlib import Path
from typing import Dict, Set

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


def get_existing_person_ids() -> Set[int]:
    if not REG_SEASON_FILE.exists():
        return set()
    existing = pd.read_csv(REG_SEASON_FILE, usecols=["person_id"])
    return set(existing["person_id"].dropna().astype(int))


def build_personid_to_name(target: pd.DataFrame) -> Dict[int, str]:
    target = target.copy()
    target["personId"] = pd.to_numeric(target.get("personId"), errors="coerce")
    mapping = {}
    for _, row in target.iterrows():
        pid = row["personId"]
        if pd.isna(pid):
            continue
        pid_int = int(pid)
        if pid_int not in mapping:
            mapping[pid_int] = row.get("Clean Name", row.get("Player Name"))
    return mapping


def find_updated_person_ids(target: pd.DataFrame, filtered: pd.DataFrame) -> Dict[int, str]:
    target = target.copy()
    target["personId"] = pd.to_numeric(target.get("personId"), errors="coerce")
    filtered_invalid = filtered[filtered["Reason"] == "invalid personId"]
    filtered_names = set(filtered_invalid["Clean Name"].astype(str))

    candidates = target[target["Clean Name"].astype(str).isin(filtered_names)]
    candidates = candidates[candidates["personId"].notna()]
    personid_to_name = build_personid_to_name(candidates)
    return personid_to_name


def append_logs(personid_to_name: Dict[int, str], existing_ids: Set[int]) -> int:
    if not personid_to_name:
        return 0
    target_ids = {pid for pid in personid_to_name.keys() if pid not in existing_ids}
    if not target_ids:
        return 0

    chunksize = 200_000
    appended_rows = 0

    # Read stats in chunks and filter
    for chunk in pd.read_csv(DATA_DIR / "PlayerStatistics.csv", low_memory=False, chunksize=chunksize):
        chunk = chunk[chunk["personId"].isin(target_ids)]
        chunk = chunk[chunk["gameType"] == "Regular Season"]
        if chunk.empty:
            continue

        chunk = chunk.copy()
        chunk["clean_name"] = chunk["personId"].map(personid_to_name)
        chunk["person_id"] = chunk["personId"]
        chunk["year"] = pd.to_datetime(chunk["gameDate"]).dt.year

        # Align columns with existing file if it exists
        if REG_SEASON_FILE.exists():
            existing_cols = pd.read_csv(REG_SEASON_FILE, nrows=1).columns.tolist()
            chunk = chunk.reindex(columns=existing_cols)

        chunk.to_csv(REG_SEASON_FILE, mode="a", header=not REG_SEASON_FILE.exists(), index=False)
        appended_rows += len(chunk)

    return appended_rows


def main() -> None:
    if not FILTERED_OUT_FILE.exists():
        raise FileNotFoundError(f"Missing {FILTERED_OUT_FILE}")

    target = read_target_players()
    filtered = read_filtered_out()
    existing_ids = get_existing_person_ids()
    personid_to_name = find_updated_person_ids(target, filtered)

    appended = append_logs(personid_to_name, existing_ids)
    print(f"Appended {appended} rows to {REG_SEASON_FILE}")


if __name__ == "__main__":
    main()
