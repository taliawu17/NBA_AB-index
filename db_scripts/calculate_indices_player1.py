#!/usr/bin/env python3
"""
NBA Player AB-Index calculation for target_player / batch 1 cohort.

Reads top games (default: output/top_games_per_season_player1.csv).
Optional override: set env CALCULATE_INDICES_PLAYER1_INPUT to another CSV path.

Outputs:
- output/player1_index.csv

Same AB rule as player2/player3; indices below 18 are reported as NA (see
calculate_indices.AB_INDEX_MIN_VALID).

Then run: python db_scripts/rank_indices_player1.py  -> output/player1_index_ranked.csv
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Union

import pandas as pd

from calculate_indices import (
    compute_ab_index_threshold,
    person_id_for_player,
    prepare_top_games_for_index,
    select_witness_row_for_export,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("index_calculation_player1.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "output"
DEFAULT_INPUT_FILE = OUTPUT_DIR / "top_games_per_season_player1.csv"


class NBAPlayerIndexCalculator:
    """AB-index calculator for batch 1."""

    def __init__(self) -> None:
        self.game_logs: pd.DataFrame | None = None
        self.player_indices: pd.DataFrame | None = None

    def load_prepared_data(self) -> None:
        data_path = Path(
            os.environ.get("CALCULATE_INDICES_PLAYER1_INPUT", str(DEFAULT_INPUT_FILE))
        )
        if not data_path.is_file():
            raise FileNotFoundError(f"Top games file not found: {data_path}")

        self.game_logs = prepare_top_games_for_index(
            pd.read_csv(data_path, low_memory=False)
        )
        logger.info(
            "Loaded %s top-game records from %s",
            f"{len(self.game_logs):,}",
            data_path.name,
        )
        logger.info("Unique players: %s", self.game_logs["player_name"].nunique())

        required_cols = ["player_name", "age_years", "points"]
        missing_cols = [c for c in required_cols if c not in self.game_logs.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

    def calculate_player_indices(self) -> None:
        if self.game_logs is None:
            raise ValueError("Data not loaded. Call load_prepared_data() first.")

        valid_data = self.game_logs[
            self.game_logs["age_years"].notna()
            & self.game_logs["points"].notna()
            & (self.game_logs["age_years"] >= 18)
        ].copy()

        logger.info(
            "Using %s records with valid age and points data",
            f"{len(valid_data):,}",
        )

        def index_for_group(g: pd.DataFrame) -> Union[int, str]:
            return compute_ab_index_threshold(g, "age_years", "points")

        index_by_player = (
            valid_data.groupby("player_name", sort=False)
            .apply(index_for_group)
            .reset_index(name="index")
        )

        detailed_info: list[dict] = []

        for player_name in index_by_player["player_name"]:
            player_data = valid_data[valid_data["player_name"] == player_name].copy()
            player_index = index_by_player[index_by_player["player_name"] == player_name][
                "index"
            ].iloc[0]

            if player_index != "NA":
                fallback = player_data.sort_values(
                    "points", ascending=False, kind="mergesort"
                ).iloc[0]
                max_game = select_witness_row_for_export(
                    player_data, player_index, fallback, "age_years", "points"
                )

                detailed_info.append(
                    {
                        "player_name": player_name,
                        "personId": person_id_for_player(player_data, max_game),
                        "index": player_index,
                        "age_years": int(max_game["age_years"]),
                        "age_days": int(max_game["age_days"])
                        if pd.notna(max_game.get("age_days"))
                        else None,
                        "pts": int(max_game["points"]),
                        "game_season": int(max_game["year"]),
                        "date_game": max_game["gameDate"],
                        "age": max_game.get("age_at_game"),
                        "Birth Date": max_game.get("birth_date"),
                    }
                )
            else:
                player_stats = player_data.groupby("player_name").agg(
                    {
                        "age_years": ["min", "max"],
                        "points": ["max"],
                        "year": ["min", "max"],
                        "birth_date": "first",
                    }
                )

                detailed_info.append(
                    {
                        "player_name": player_name,
                        "personId": person_id_for_player(player_data),
                        "index": "NA",
                        "age_years": None,
                        "age_days": None,
                        "pts": None,
                        "game_season": None,
                        "date_game": None,
                        "age": None,
                        "Birth Date": player_stats.iloc[0][("birth_date", "first")],
                    }
                )

        self.player_indices = pd.DataFrame(detailed_info)
        logger.info("Calculated indices for %s players", len(self.player_indices))

    def save_results(self) -> None:
        if self.player_indices is None:
            raise ValueError("No indices calculated.")

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_DIR / "player1_index.csv"
        self.player_indices.to_csv(out_path, index=False)
        logger.info("Saved player indices to %s", out_path)

    def generate_summary_report(self) -> None:
        print("\n" + "=" * 80)
        print("NBA PLAYER INDEX CALCULATION (BATCH 1) - SUMMARY")
        print("=" * 80)

        if self.player_indices is None:
            print("No indices calculated yet.")
            return

        valid_indices = self.player_indices[self.player_indices["index"] != "NA"].copy()
        if len(valid_indices) > 0:
            valid_indices["index"] = valid_indices["index"].astype(int)

        print(f"\nTotal players: {len(self.player_indices):,}")
        print(f"Valid index: {len(valid_indices):,}")
        print(f"NA index: {len(self.player_indices) - len(valid_indices):,}")

        if len(valid_indices) > 0:
            print(
                f"\nIndex range: {valid_indices['index'].min()}-{valid_indices['index'].max()}"
            )
            top_players = valid_indices.sort_values(
                ["index", "pts", "age_years", "age_days"],
                ascending=[False, False, False, False],
            ).head(20)
            print("\nTop players by index:")
            for i, (_, player) in enumerate(top_players.iterrows(), 1):
                print(
                    f"{i:2d}. {player['player_name']:<25} Index: {int(player['index']):2d} "
                    f"(Age: {player['age_years']:.0f}, Pts: {player['pts']:.0f})"
                )

        print("\n" + "=" * 80)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    logger.info("Starting NBA Player Index calculation (batch 1)...")
    calc = NBAPlayerIndexCalculator()
    calc.load_prepared_data()
    calc.calculate_player_indices()
    calc.save_results()
    calc.generate_summary_report()
    logger.info("Done. Next: python db_scripts/rank_indices_player1.py")


if __name__ == "__main__":
    main()
