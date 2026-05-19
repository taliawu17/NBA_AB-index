#!/usr/bin/env python3
"""
Extract ALL game logs for players in target_player3_with_personId.csv
(clean_name -> [personId]). Adds person_id and clean_name columns.

Outputs (batch 3 only; does not overwrite batch 2 files):
- output/all_player3_game_logs.csv
- output/all_player3_game_logs_regular_season.csv
- output/duplicate_players_target3.txt
- output/missing_personid_players_target3.csv

Uses data/up2_2526/PlayerStatistics.csv (2025-26-inclusive), not data/PlayerStatistics.csv.

Run order: 1) this script
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
FALLBACK_DATA_DIR = BASE_DIR.parent / "data"
TARGET3_FILE = DATA_DIR / "target_player3_with_personId.csv"
if not TARGET3_FILE.exists():
    TARGET3_FILE = FALLBACK_DATA_DIR / "target_player3_with_personId.csv"
OUTPUT_DIR = BASE_DIR / "output"
STATS_FILE = DATA_DIR / "up2_2526" / "PlayerStatistics.csv"
if not STATS_FILE.exists():
    STATS_FILE = FALLBACK_DATA_DIR / "up2_2526" / "PlayerStatistics.csv"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("game_log_extraction_target3.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def read_target3() -> pd.DataFrame:
    try:
        return pd.read_csv(TARGET3_FILE)
    except UnicodeDecodeError:
        return pd.read_csv(TARGET3_FILE, encoding="latin1")


def main() -> None:
    if not DATA_DIR.exists() and not FALLBACK_DATA_DIR.exists():
        raise FileNotFoundError("Missing data directory")
    if not TARGET3_FILE.exists():
        raise FileNotFoundError(f"Missing {TARGET3_FILE}")

    logger.info("Loading PlayerStatistics from %s ...", STATS_FILE)
    if not STATS_FILE.exists():
        raise FileNotFoundError(
            f"Missing {STATS_FILE}. Place the updated PlayerStatistics.csv under data/up2_2526/."
        )
    stats = pd.read_csv(STATS_FILE, low_memory=False)
    stats["gameDate"] = pd.to_datetime(stats["gameDate"], errors="coerce")
    logger.info("Loading target_player3_with_personId.csv...")
    target3 = read_target3()

    if "personId" not in target3.columns or "Clean Name" not in target3.columns:
        raise ValueError("target_player3_with_personId.csv must contain personId and Clean Name")

    player_name_mapping: Dict[str, List[int]] = {}
    missing_personid: list[dict[str, str]] = []

    for _, row in target3.iterrows():
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
            logger.warning("Missing personId for %s; skipping player.", clean_name)
        except UnicodeEncodeError:
            logger.warning("Missing personId for player (Unicode name); skipping player.")
        missing_personid.append({"clean_name": str(clean_name), "player_name": str(player_name)})
        if clean_name not in player_name_mapping:
            player_name_mapping[clean_name] = []

    logger.info(
        "Target players with personId: %s",
        sum(len(v) for v in player_name_mapping.values()),
    )

    all_player_logs: list[pd.DataFrame] = []
    duplicate_players: list[dict] = []

    for clean_name, person_ids in player_name_mapping.items():
        logger.info("Processing %s (%s personIds)", clean_name, len(person_ids))
        player_results: list[pd.DataFrame] = []

        for person_id in person_ids:
            player_games = stats[stats["personId"] == person_id].copy()
            if len(player_games) == 0:
                logger.warning("No games found for %s (personId: %s)", clean_name, person_id)
                continue
            player_games["clean_name"] = clean_name
            player_games["person_id"] = person_id
            player_games["year"] = player_games["gameDate"].dt.year
            player_games = player_games.sort_values("gameDate")
            player_results.append(player_games)
            logger.info("  Found %s games for %s (personId: %s)", len(player_games), clean_name, person_id)

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
                logger.info("  DUPLICATE: %s has %s personIds", clean_name, len(person_ids))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if all_player_logs:
        combined_logs = pd.concat(all_player_logs, ignore_index=True)
        output_file = OUTPUT_DIR / "all_player3_game_logs.csv"
        combined_logs.to_csv(output_file, index=False)
        logger.info("Saved %s rows to %s", f"{len(combined_logs):,}", output_file)

        regular_season = combined_logs[combined_logs["gameType"] == "Regular Season"].copy()
        regular_file = OUTPUT_DIR / "all_player3_game_logs_regular_season.csv"
        regular_season.to_csv(regular_file, index=False)
        logger.info("Saved regular season logs to %s", regular_file)

    if duplicate_players:
        duplicate_file = OUTPUT_DIR / "duplicate_players_target3.txt"
        with open(duplicate_file, "w", encoding="utf-8") as f:
            f.write("NBA Player Duplicate Analysis (target3)\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Total players with duplicate personIds: {len(duplicate_players)}\n\n")
            for dup in duplicate_players:
                f.write(f"Player: {dup['clean_name']}\n")
                f.write(f"PersonIds: {dup['person_ids']}\n")
                f.write(f"Total Games: {dup['total_games']}\n")
                f.write("-" * 30 + "\n")
        logger.info("Saved duplicate player information to %s", duplicate_file)

    if missing_personid:
        missing_file = OUTPUT_DIR / "missing_personid_players_target3.csv"
        pd.DataFrame(missing_personid).to_csv(missing_file, index=False)
        logger.info("Saved missing personId report to %s", missing_file)


if __name__ == "__main__":
    main()
