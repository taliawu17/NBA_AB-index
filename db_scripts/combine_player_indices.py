#!/usr/bin/env python3
"""
Combine batch 1–3 index CSVs, dedupe by personId, rank valid indices.

Batch 3 players may also appear in batch 1 and/or 2. After stacking, keep one
row per player: highest index; ties broken by age_years, then age_days (desc).

Inputs:
  output/player1_index.csv
  output/player2_index.csv
  output/player3_index.csv

Outputs:
  output/player_index_all.csv          — one row per personId (all indices incl. NA); AB_rank for ranked players
  output/player_index_ranked_all.csv   — valid index only (>= 18), sorted; AB_rank 1..N
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "output"

BATCH_FILES = (
    ("batch1", OUTPUT_DIR / "player1_index.csv"),
    ("batch2", OUTPUT_DIR / "player2_index.csv"),
    ("batch3", OUTPUT_DIR / "player3_index.csv"),
)

ALL_OUT = OUTPUT_DIR / "player_index_all.csv"
RANKED_ALL_OUT = OUTPUT_DIR / "player_index_ranked_all.csv"


def _save_csv(df: pd.DataFrame, path: Path) -> Path:
    try:
        df.to_csv(path, index=False)
        return path
    except PermissionError:
        alt = path.parent / f"{path.stem}_new{path.suffix}"
        df.to_csv(alt, index=False)
        print(f"Permission denied for {path}; wrote {alt}")
        return alt


def _player_key(df: pd.DataFrame) -> pd.Series:
    """Dedupe key: personId when present, else normalized player_name."""
    if "personId" in df.columns:
        pid = pd.to_numeric(df["personId"], errors="coerce")
        name = df["player_name"].astype(str).str.strip().str.lower()
        return pid.where(pid.notna(), other=pd.NA).astype("Int64").astype(str).where(
            pid.notna(), other="name:" + name
        )
    return "name:" + df["player_name"].astype(str).str.strip().str.lower()


def load_and_stack(paths: tuple[tuple[str, Path], ...] | None = None) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for label, path in paths or BATCH_FILES:
        if not path.is_file():
            raise FileNotFoundError(f"Missing {path} (run calculate_indices for {label})")
        part = pd.read_csv(path, low_memory=False)
        part["source_batch"] = label
        frames.append(part)
    return pd.concat(frames, ignore_index=True)


def dedupe_players(stacked: pd.DataFrame) -> pd.DataFrame:
    work = stacked.copy()
    work["_player_key"] = _player_key(work)
    work["_index_num"] = pd.to_numeric(work["index"], errors="coerce")
    work["_age_years"] = pd.to_numeric(work["age_years"], errors="coerce")
    work["_age_days"] = pd.to_numeric(work["age_days"], errors="coerce")

    work = work.sort_values(
        ["_index_num", "_age_years", "_age_days"],
        ascending=[False, False, False],
        na_position="last",
        kind="mergesort",
    )
    deduped = work.drop_duplicates(subset=["_player_key"], keep="first")
    return deduped.drop(columns=["_player_key", "_index_num", "_age_years", "_age_days"])


def rank_valid(deduped: pd.DataFrame) -> pd.DataFrame:
    idx_num = pd.to_numeric(deduped["index"], errors="coerce")
    valid = deduped.loc[idx_num.notna()].copy()
    valid["index"] = idx_num.loc[valid.index].astype(int)
    valid = valid.loc[valid["index"] >= 18].copy()
    valid["age_years"] = pd.to_numeric(valid["age_years"], errors="coerce")
    valid["age_days"] = pd.to_numeric(valid["age_days"], errors="coerce")
    valid["pts"] = pd.to_numeric(valid["pts"], errors="coerce")
    return valid.sort_values(
        ["index", "pts", "age_years", "age_days"],
        ascending=[False, False, False, False],
        kind="mergesort",
    )


def assign_ab_rank(ranked: pd.DataFrame) -> pd.DataFrame:
    """AB_rank 1..N in sort order (index → pts → age_years → age_days, descending)."""
    out = ranked.copy()
    out["AB_rank"] = range(1, len(out) + 1)
    return _place_ab_rank_column(out)


def attach_ab_rank_to_all(deduped: pd.DataFrame, ranked: pd.DataFrame) -> pd.DataFrame:
    """Map AB_rank onto full deduped table; NA / index < 18 leave AB_rank empty."""
    keys = _player_key(deduped)
    rank_by_key = ranked.assign(_player_key=_player_key(ranked)).set_index("_player_key")["AB_rank"]
    out = deduped.copy()
    out["AB_rank"] = keys.map(rank_by_key)
    return _place_ab_rank_column(out)


def _place_ab_rank_column(df: pd.DataFrame) -> pd.DataFrame:
    cols = df.columns.tolist()
    if "AB_rank" in cols:
        cols.remove("AB_rank")
    if "index" in cols:
        cols.insert(cols.index("index") + 1, "AB_rank")
    else:
        cols.append("AB_rank")
    return df[cols]


def main() -> None:
    parser = argparse.ArgumentParser(description="Combine and dedupe batch 1–3 indices")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    stacked = load_and_stack()
    print(f"Stacked rows: {len(stacked):,} (before dedupe)")
    print(stacked.groupby("source_batch").size().to_string())

    deduped = dedupe_players(stacked)
    dup_removed = len(stacked) - len(deduped)
    print(f"After dedupe: {len(deduped):,} players ({dup_removed:,} duplicate rows removed)")

    if "personId" in stacked.columns:
        b3_ids = set(
            pd.to_numeric(
                stacked.loc[stacked["source_batch"] == "batch3", "personId"],
                errors="coerce",
            ).dropna().astype(int)
        )
        for label in ("batch1", "batch2"):
            ids = set(
                pd.to_numeric(
                    stacked.loc[stacked["source_batch"] == label, "personId"],
                    errors="coerce",
                ).dropna().astype(int)
            )
            overlap = b3_ids & ids
            if overlap:
                print(f"  batch3 personIds also in {label}: {len(overlap)}")

    ranked = assign_ab_rank(rank_valid(deduped))
    all_with_rank = attach_ab_rank_to_all(deduped, ranked)
    all_path = _save_csv(all_with_rank, out_dir / ALL_OUT.name)
    ranked_path = _save_csv(ranked, out_dir / RANKED_ALL_OUT.name)
    print(f"Saved: {all_path} ({len(deduped):,} rows)")
    print(f"Saved: {ranked_path} ({len(ranked):,} ranked rows)")


if __name__ == "__main__":
    main()
