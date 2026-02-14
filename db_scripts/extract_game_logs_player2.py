#!/usr/bin/env python3
"""
Extract ALL game logs for players in target_player2_with_personId.csv
using a clean_name -> [personId] mapping. Adds person_id and clean_name columns.
Generates duplicate-personId and missing-personId reports.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
FALLBACK_DATA_DIR = BASE_DIR.parent / "data"
TARGET2_FILE = DATA_DIR / "target_player2_with_personId.csv"
if not TARGET2_FILE.exists():
    TARGET2_FILE = FALLBACK_DATA_DIR / "target_player2_with_personId.csv"
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
    if not DATA_DIR.exists() and not FALLBACK_DATA_DIR.exists():
        raise FileNotFoundError("Missing data directory")
    if not TARGET2_FILE.exists():
        raise FileNotFoundError(f"Missing {TARGET2_FILE}")

    logger.info("Loading PlayerStatistics.csv...")
    stats_file = DATA_DIR / "PlayerStatistics.csv"
    if not stats_file.exists():
        stats_file = FALLBACK_DATA_DIR / "PlayerStatistics.csv"
    stats = pd.read_csv(stats_file, low_memory=False)
    stats["gameDate"] = pd.to_datetime(stats["gameDate"], errors="coerce")
    logger.info("Loading target_player2_with_personId.csv...")
    target2 = read_target2()

    if "personId" not in target2.columns or "Clean Name" not in target2.columns:
        raise ValueError("target_player2_with_personId.csv must contain personId and Clean Name")

    # Build clean_name -> [personId] mapping (skip missing personId)
    player_name_mapping: Dict[str, List[int]] = {}
    missing_personid = []

    for _, row in target2.iterrows():
        clean_name = row.get("Clean Name")
        player_name = row.get("Player Name", clean_name)
        person_id = row.get("personId")

        if pd.notna(person_id):
            pid = int(person_id)
            if clean_name not in player_name_mapping:
                player_name_mapping[clean_name] = []
            if pid not in player_name_mapping[clean_name]:
                player_name_mapping[clean_name].append(pid)
            continue

        try:
            logger.warning(f"Missing personId for {clean_name}; skipping player.")
        except UnicodeEncodeError:
            logger.warning("Missing personId for player (Unicode name); skipping player.")
        missing_personid.append({"clean_name": clean_name, "player_name": player_name})
        if clean_name not in player_name_mapping:
            player_name_mapping[clean_name] = []

    logger.info(
        f"Target players with personId: {sum(len(v) for v in player_name_mapping.values())}"
    )

    all_player_logs = []
    duplicate_players = []

    for clean_name, person_ids in player_name_mapping.items():
        logger.info(f"Processing {clean_name} ({len(person_ids)} personIds)")
        player_results = []

        for person_id in person_ids:
            player_games = stats[stats["personId"] == person_id].copy()
            if len(player_games) == 0:
                logger.warning(f"No games found for {clean_name} (personId: {person_id})")
                continue
            player_games["clean_name"] = clean_name
            player_games["person_id"] = person_id
            player_games["year"] = player_games["gameDate"].dt.year
            player_games = player_games.sort_values("gameDate")
            player_results.append(player_games)
            logger.info(f"  Found {len(player_games)} games for {clean_name} (personId: {person_id})")

        if player_results:
            combined_results = pd.concat(player_results, ignore_index=True)
            all_player_logs.append(combined_results)
            if len(person_ids) > 1:
                duplicate_players.append(
                    {
                        "clean_name": clean_name,
                        "person_ids": person_ids,
                        "total_games": len(combined_results),
                    }
                )
                logger.info(f"  DUPLICATE: {clean_name} has {len(person_ids)} personIds")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if all_player_logs:
        combined_logs = pd.concat(all_player_logs, ignore_index=True)
        output_file = OUTPUT_DIR / "all_player2_game_logs.csv"
        combined_logs.to_csv(output_file, index=False)
        logger.info(f"Saved {len(combined_logs):,} rows to {output_file}")

        regular_season = combined_logs[combined_logs["gameType"] == "Regular Season"].copy()
        regular_file = OUTPUT_DIR / "player2_game_logs_regular_season.csv"
        regular_season.to_csv(regular_file, index=False)
        logger.info(f"Saved regular season logs to {regular_file}")

    if duplicate_players:
        duplicate_file = OUTPUT_DIR / "duplicate_players_target2.txt"
        with open(duplicate_file, "w", encoding="utf-8") as f:
            f.write("NBA Player Duplicate Analysis (target2)\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Total players with duplicate personIds: {len(duplicate_players)}\n\n")
            for dup in duplicate_players:
                f.write(f"Player: {dup['clean_name']}\n")
                f.write(f"PersonIds: {dup['person_ids']}\n")
                f.write(f"Total Games: {dup['total_games']}\n")
                f.write("-" * 30 + "\n")
        logger.info(f"Saved duplicate player information to {duplicate_file}")

    if missing_personid:
        missing_file = OUTPUT_DIR / "missing_personid_players_target2.csv"
        pd.DataFrame(missing_personid).to_csv(missing_file, index=False)
        logger.info(f"Saved missing personId report to {missing_file}")


if __name__ == "__main__":
    main()
