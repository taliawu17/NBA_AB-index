#!/usr/bin/env python3
"""
Generate a CSV of target players that do not match PlayerStatistics.csv.

Definition of "missing":
- No exact full-name match against PlayerStatistics.csv
"""

from pathlib import Path
import unicodedata

import pandas as pd


def normalize_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    normalized = unicodedata.normalize("NFD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_name = ascii_name.replace("*", "").strip()
    return " ".join(ascii_name.lower().split())


def main() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / "data"
    output_dir = base_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    stats = pd.read_csv(data_dir / "PlayerStatistics.csv", low_memory=False)
    target = pd.read_csv(data_dir / "target_player.csv")

    stats_full = (stats["firstName"].fillna("") + " " + stats["lastName"].fillna("")).str.strip()
    stats_full_set = set(stats_full)
    stats_norm_set = set(stats_full.map(normalize_name))

    target_names = target["Clean Name"].astype(str).str.strip()
    target_norm = target_names.map(normalize_name)

    exact_match = target_names.isin(stats_full_set)
    normalized_match = target_norm.isin(stats_norm_set)

    missing = target.loc[~exact_match].copy()
    missing["Exact Match"] = False
    missing["Normalized Match"] = normalized_match.loc[missing.index]

    output_path = output_dir / "missing_target_players.csv"
    missing.to_csv(output_path, index=False)

    print(f"Missing target players saved to: {output_path}")
    print(f"Total missing (exact match): {len(missing)}")


if __name__ == "__main__":
    main()
