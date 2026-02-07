#!/usr/bin/env python3
"""
NBA Player AB-Index Calculation Script (player2)

This script calculates the index for each player based on the rule:
- For each player, find the first age_years (scanning from largest to smallest)
- where points >= age_years
- If none found, return "NA"

Date: 2026
"""

import sys
import pandas as pd
import numpy as np
import os
from pathlib import Path
from typing import List, Tuple, Union
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('index_calculation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

class NBAPlayerIndexCalculator:
    """Class for calculating NBA player indices"""

    def __init__(self, data_dir: str = "."):
        """
        Initialize the calculator

        Args:
            data_dir: Directory containing the data files
        """
        self.data_dir = data_dir
        self.game_logs = None
        self.player_indices = None

    def load_prepared_data(self):
        """Load the prepared regular season data"""
        logger.info("Loading prepared regular season data...")

        try:
            data_file = OUTPUT_DIR / "top2_games_per_season_with_birthdate_player2 - Copy.csv"
            if not os.path.exists(data_file):
                raise FileNotFoundError(f"Prepared data file not found: {data_file}")

            self.game_logs = pd.read_csv(data_file)
            logger.info(f"Loaded {len(self.game_logs):,} regular season records")
            logger.info(f"Unique players: {self.game_logs['player_name'].nunique():,}")

            required_cols = ['player_name', 'age_years', 'points']
            missing_cols = [col for col in required_cols if col not in self.game_logs.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")

            logger.info("Data loading completed successfully!")

        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise

    def calculate_player_indices(self):
        """Calculate the index for each player"""
        logger.info("Calculating player indices...")

        if self.game_logs is None:
            raise ValueError("Data not loaded. Call load_prepared_data() first.")

        valid_data = self.game_logs[
            self.game_logs['age_years'].notna()
            & self.game_logs['points'].notna()
            & (self.game_logs['age_years'] >= 18)
        ].copy()

        logger.info(f"Using {len(valid_data):,} records with valid age and points data")

        def index_for_group(g: pd.DataFrame) -> Union[int, str]:
            g_sorted = g.sort_values('age_years', ascending=False, kind="mergesort")
            for i, (_, row) in enumerate(g_sorted.iterrows()):
                current_age = int(row['age_years'])
                records_from_highest_down = g_sorted.iloc[:i + 1]
                max_points_from_highest_down = records_from_highest_down['points'].max()
                if max_points_from_highest_down >= current_age:
                    return current_age
            return "NA"

        self.player_indices = (
            valid_data.groupby('player_name', sort=False)
            .apply(index_for_group)
            .reset_index(name="index")
        )

        detailed_info = []

        for player_name in self.player_indices['player_name']:
            player_data = valid_data[valid_data['player_name'] == player_name].copy()
            player_index = self.player_indices[self.player_indices['player_name'] == player_name]['index'].iloc[0]

            if player_index != "NA":
                player_data_sorted = player_data.sort_values('age_years', ascending=False)

                for i, (_, row) in enumerate(player_data_sorted.iterrows()):
                    current_age = int(row['age_years'])
                    records_from_highest_down = player_data_sorted.iloc[:i + 1]
                    max_points_from_highest_down = records_from_highest_down['points'].max()

                    if max_points_from_highest_down >= current_age:
                        max_game = records_from_highest_down[
                            records_from_highest_down['points'] == max_points_from_highest_down
                        ].iloc[0]

                        detailed_info.append({
                            'player_name': player_name,
                            'index': player_index,
                            'age_years': int(max_game['age_years']),
                            'age_days': int(max_game['age_days']) if pd.notna(max_game.get('age_days')) else None,
                            'pts': int(max_game['points']),
                            'game_season': int(max_game['year']),
                            'date_game': max_game['gameDate'],
                            'age': max_game['age_at_game'],
                            'Birth Date': max_game['birth_date']
                        })
                        break
            else:
                player_stats = player_data.groupby('player_name').agg({
                    'age_years': ['min', 'max'],
                    'points': ['max'],
                    'year': ['min', 'max'],
                    'birth_date': 'first'
                }).round(2)

                detailed_info.append({
                    'player_name': player_name,
                    'index': "NA",
                    'age_years': None,
                    'age_days': None,
                    'pts': None,
                    'game_season': None,
                    'date_game': None,
                    'age': None,
                    'Birth Date': player_stats.iloc[0][('birth_date', 'first')]
                })

        self.player_indices = pd.DataFrame(detailed_info)

        logger.info(f"Calculated indices for {len(self.player_indices):,} players")

        valid_indices = self.player_indices[self.player_indices['index'] != 'NA']
        na_indices = self.player_indices[self.player_indices['index'] == 'NA']

        logger.info(f"Players with valid index: {len(valid_indices):,}")
        logger.info(f"Players with NA index: {len(na_indices):,}")

        if len(valid_indices) > 0:
            logger.info(
                f"Index statistics: Min={valid_indices['index'].min():.0f}, "
                f"Max={valid_indices['index'].max():.0f}, Mean={valid_indices['index'].mean():.1f}"
            )

    def save_results(self, output_dir: str = str(OUTPUT_DIR)):
        """Save the calculated indices to files"""
        logger.info("Saving index calculation results...")

        if self.player_indices is None:
            raise ValueError("No indices calculated. Call calculate_player_indices() first.")

        os.makedirs(output_dir, exist_ok=True)

        indices_file = os.path.join(output_dir, 'player_indices_player2_20260206.csv')
        self.player_indices.to_csv(indices_file, index=False)
        logger.info(f"Saved player indices to {indices_file}")

        sorted_indices = self.player_indices.copy()
        valid_indices = sorted_indices[sorted_indices['index'] != 'NA'].copy()
        valid_indices['index'] = valid_indices['index'].astype(int)
        valid_indices['age_days'] = pd.to_numeric(valid_indices['age_days'], errors='coerce')
        valid_indices['pts'] = pd.to_numeric(valid_indices['pts'], errors='coerce')
        valid_indices = valid_indices.sort_values(['index', 'pts', 'age_days'], ascending=[False, False, False])

        sorted_file = os.path.join(output_dir, 'player_indices_ranked_player2_20260206.csv')
        valid_indices.to_csv(sorted_file, index=False)
        logger.info(f"Saved ranked player indices to {sorted_file}")

        excel_file = os.path.join(output_dir, 'player_indices_player2_20260206.xlsx')
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            self.player_indices.to_excel(writer, sheet_name='All Players', index=False)
            valid_indices.to_excel(writer, sheet_name='Ranked Players', index=False)

            summary_data = {
                'Metric': [
                    'Total Players',
                    'Players with Valid Index',
                    'Players with NA Index',
                    'Index Range',
                    'Average Index',
                    'Highest Index',
                    'Lowest Index'
                ],
                'Value': [
                    len(self.player_indices),
                    len(valid_indices),
                    len(self.player_indices) - len(valid_indices),
                    f"{int(valid_indices['index'].min())}-{int(valid_indices['index'].max())}" if len(valid_indices) > 0 else "N/A",
                    f"{valid_indices['index'].mean():.1f}" if len(valid_indices) > 0 else "N/A",
                    f"{int(valid_indices['index'].max())}" if len(valid_indices) > 0 else "N/A",
                    f"{int(valid_indices['index'].min())}" if len(valid_indices) > 0 else "N/A"
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

        logger.info(f"Saved Excel file to {excel_file}")

        parquet_file = os.path.join(output_dir, 'player_indices_player2_20260206.parquet')
        parquet_data = self.player_indices.copy()
        parquet_data['index'] = pd.to_numeric(parquet_data['index'], errors='coerce')
        parquet_data.to_parquet(parquet_file, index=False)
        logger.info(f"Saved Parquet file to {parquet_file}")

    def generate_summary_report(self):
        """Generate a summary report of the index calculation"""
        logger.info("Generating summary report...")

        print("\n" + "=" * 80)
        print("NBA PLAYER INDEX CALCULATION - SUMMARY REPORT")
        print("=" * 80)

        if self.player_indices is None:
            print("No indices calculated yet.")
            return

        valid_indices = self.player_indices[self.player_indices['index'] != 'NA'].copy()
        valid_indices['index'] = valid_indices['index'].astype(int)

        print(f"\nIndex Calculation Results:")
        print("-" * 40)
        print(f"Total Players: {len(self.player_indices):,}")
        print(f"Players with Valid Index: {len(valid_indices):,}")
        print(f"Players with NA Index: {len(self.player_indices) - len(valid_indices):,}")

        if len(valid_indices) > 0:
            print(f"\nIndex Statistics:")
            print("-" * 20)
            print(f"Range: {valid_indices['index'].min()}-{valid_indices['index'].max()}")
            print(f"Average: {valid_indices['index'].mean():.1f}")
            print(f"Median: {valid_indices['index'].median():.1f}")

            print(f"\nTop 20 Players by Index:")
            print("-" * 50)
            top_players = valid_indices.sort_values('index', ascending=False).head(20)
            for i, (_, player) in enumerate(top_players.iterrows(), 1):
                print(
                    f"{i:2d}. {player['player_name']:<25} "
                    f"Index: {player['index']:2.0f} "
                    f"(Age: {player['age_years']:.0f}, Pts: {player['pts']:.0f})"
                )

        print("\n" + "=" * 80)


def main():
    """Main execution function"""
    logger.info("Starting NBA Player Index Calculation...")

    calculator = NBAPlayerIndexCalculator()

    try:
        calculator.load_prepared_data()
        calculator.calculate_player_indices()
        calculator.save_results()
        calculator.generate_summary_report()
        logger.info("Index calculation completed successfully!")

    except Exception as e:
        logger.error(f"Index calculation failed: {e}")
        raise


if __name__ == "__main__":
    main()
