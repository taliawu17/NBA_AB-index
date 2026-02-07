#!/usr/bin/env python3
"""
Extract ALL game logs for players in target_player2_with_personId.csv
using personId as key. Adds person_id and clean_name columns.
"""

import logging
import os
import sys
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
TARGET2_FILE = DATA_DIR / "target_player2_with_personId.csv"
OUTPUT_DIR = BASE_DIR / "output"


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("game_log_extraction_target2.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def read_target2() -> pd.DataFrame:
    try:
        return pd.read_csv(TARGET2_FILE)
    except UnicodeDecodeError:
        return pd.read_csv(TARGET2_FILE, encoding="latin1")


def main() -> None:
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Missing {DATA_DIR}")
    if not TARGET2_FILE.exists():
        raise FileNotFoundError(f"Missing {TARGET2_FILE}")

    logger.info("Loading PlayerStatistics.csv...")
    stats = pd.read_csv(DATA_DIR / "PlayerStatistics.csv", low_memory=False)
    stats["gameDate"] = pd.to_datetime(stats["gameDate"], errors="coerce")
    logger.info("Loading target_player2_with_personId.csv...")
    target2 = read_target2()

    if "personId" not in target2.columns or "Clean Name" not in target2.columns:
        raise ValueError("target_player2_with_personId.csv must contain personId and Clean Name")

    target2["personId"] = pd.to_numeric(target2["personId"], errors="coerce")
    target2 = target2[target2["personId"].notna()].copy()
    target2["personId"] = target2["personId"].astype(int)

    id_to_name = dict(zip(target2["personId"], target2["Clean Name"]))
    target_ids = set(id_to_name.keys())
    logger.info(f"Target players with personId: {len(target_ids)}")

    # Filter all logs for target personIds
    filtered = stats[stats["personId"].isin(target_ids)].copy()
    filtered["clean_name"] = filtered["personId"].map(id_to_name)
    filtered["person_id"] = filtered["personId"]
    filtered["year"] = filtered["gameDate"].dt.year

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "all_player2_game_logs.csv"
    filtered.to_csv(output_file, index=False)
    logger.info(f"Saved {len(filtered):,} rows to {output_file}")


if __name__ == "__main__":
    main()
