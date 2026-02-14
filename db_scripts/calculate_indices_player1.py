#!/usr/bin/env python3
"""
NBA Player AB-Index Calculation Script

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
FALLBACK_OUTPUT_DIR = BASE_DIR.parent / "output"
def compute_index_from_pairs(pairs: List[Tuple[int, int]]) -> Union[int, str]:
    """
    Given a list of (age_years, points) pairs for one individual,
    return the first age_years (scanning from largest age to smallest)
    where points >= age_years. If none, return "NA".
    """
    for age, pts in sorted(pairs, key=lambda x: x[0], reverse=True):
        if pts >= age:
            return age
    return "NA"

def compute_indices_csv(input_csv: str,
                       output_csv: str,
                       id_col: str = "id",
                       age_col: str = "age_years",
                       pts_col: str = "points") -> None:
    """
    Read input CSV with columns [id_col, age_col, pts_col],
    compute the index per individual, and write results to output_csv.
    The output has columns [id_col, index].
    """
    df = pd.read_csv(input_csv)

    def index_for_group(g: pd.DataFrame) -> Union[int, str]:
        # Stable sort so duplicates keep original order if that matters
        g_sorted = g.sort_values(age_col, ascending=False, kind="mergesort")
        mask = g_sorted[pts_col] >= g_sorted[age_col]
        if not mask.any():
            return "NA"
        return int(g_sorted.loc[mask, age_col].iloc[0])

    result = (
        df.groupby(id_col, sort=False)
          .apply(index_for_group)
          .reset_index(name="index")
    )
    result.to_csv(output_csv, index=False)

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
        self.output_dir = OUTPUT_DIR
        
    def load_prepared_data(self):
        """Load the prepared regular season data"""
        logger.info("Loading prepared regular season data...")
        
        try:
            # Load the prepared regular season data
            data_file = OUTPUT_DIR / "player1_key_game_logs - Copy.csv"
            if not os.path.exists(data_file):
                data_file = FALLBACK_OUTPUT_DIR / "player1_key_game_logs - Copy.csv"
            if not os.path.exists(data_file):
                raise FileNotFoundError(f"Prepared data file not found: {data_file}")
            
            self.game_logs = pd.read_csv(data_file)
            self.output_dir = data_file.parent
            logger.info(f"Loaded {len(self.game_logs):,} regular season records")
            logger.info(f"Unique players: {self.game_logs['clean_name'].nunique():,}")
            
            # Check required columns
            required_cols = ['clean_name', 'age_years', 'points']
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
        
        # Filter out records with invalid age data
        # Also filter out impossible ages (under 18 for NBA players)
        valid_data = self.game_logs[
            self.game_logs['age_years'].notna() & 
            self.game_logs['points'].notna() &
            (self.game_logs['age_years'] >= 18)  # NBA players must be at least 18
        ].copy()
        
        logger.info(f"Using {len(valid_data):,} records with valid age and points data")
        
        # Calculate index for each player
        def index_for_group(g: pd.DataFrame) -> Union[int, str]:
            # Sort by age_years (highest to lowest), then points, then gameDate
            g_sorted = g.sort_values(
                ['age_years', 'points', 'gameDate'],
                ascending=[False, False, False],
                kind="mergesort"
            )
            
            # For each age (from highest to lowest), check if the highest score
            # among ALL ages from highest down to current age >= current age
            for i, (_, row) in enumerate(g_sorted.iterrows()):
                current_age = int(row['age_years'])
                
                # Get all records from highest age down to current age (including current age)
                records_from_highest_down = g_sorted.iloc[:i+1]
                
                # Check if the highest score among these records >= current_age
                max_points_from_highest_down = records_from_highest_down['points'].max()
                
                if max_points_from_highest_down >= current_age:
                    return current_age
            
            return "NA"
        
        self.player_indices = (
            valid_data.groupby('clean_name', sort=False)
            .apply(index_for_group)
            .reset_index(name="index")
        )
        
        # Add detailed information for each player's index calculation
        detailed_info = []
        
        for player_name in self.player_indices['clean_name']:
            player_data = valid_data[valid_data['clean_name'] == player_name].copy()
            player_index = self.player_indices[self.player_indices['clean_name'] == player_name]['index'].iloc[0]
            
            if player_index != "NA":
                # Find the specific record that determined the index
                player_data_sorted = player_data.sort_values(
                    ['age_years', 'points', 'gameDate'],
                    ascending=[False, False, False],
                    kind="mergesort"
                )
                
                for i, (_, row) in enumerate(player_data_sorted.iterrows()):
                    current_age = int(row['age_years'])
                    
                    # Get all records from highest age down to current age (including current age)
                    records_from_highest_down = player_data_sorted.iloc[:i+1]
                    max_points_from_highest_down = records_from_highest_down['points'].max()
                    
                    if max_points_from_highest_down >= current_age:
                        # Find the specific game where max_points_from_highest_down was achieved
                        max_game = records_from_highest_down[records_from_highest_down['points'] == max_points_from_highest_down].iloc[0]
                        
                        detailed_info.append({
                            'player_name': player_name,
                            'personId': int(max_game['personId']) if pd.notna(max_game.get('personId')) else None,
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
                # For NA cases, add basic info
                player_stats = player_data.groupby('clean_name').agg({
                    'age_years': ['min', 'max'],
                    'points': ['max'],
                    'year': ['min', 'max'],
                    'birth_date': 'first'
                }).round(2)
                person_ids = player_data["personId"].dropna().unique()
                person_id_value = int(person_ids[0]) if len(person_ids) == 1 else None
                
                detailed_info.append({
                    'player_name': player_name,
                    'personId': person_id_value,
                    'index': "NA",
                    'age_years': None,
                    'age_days': None,
                    'pts': None,
                    'game_season': None,
                    'date_game': None,
                    'age': None,
                    'Birth Date': player_stats.iloc[0][('birth_date', 'first')]
                })
        
        # Convert to DataFrame
        self.player_indices = pd.DataFrame(detailed_info)
        
        logger.info(f"Calculated indices for {len(self.player_indices):,} players")
        
        # Show statistics
        valid_indices = self.player_indices[self.player_indices['index'] != 'NA']
        na_indices = self.player_indices[self.player_indices['index'] == 'NA']
        
        logger.info(f"Players with valid index: {len(valid_indices):,}")
        logger.info(f"Players with NA index: {len(na_indices):,}")
        
        if len(valid_indices) > 0:
            logger.info(f"Index statistics: Min={valid_indices['index'].min():.0f}, Max={valid_indices['index'].max():.0f}, Mean={valid_indices['index'].mean():.1f}")
    
    def save_results(self, output_dir: str = None):
        """Save the calculated indices to files"""
        logger.info("Saving index calculation results...")
        
        if self.player_indices is None:
            raise ValueError("No indices calculated. Call calculate_player_indices() first.")
        
        # Create output directory
        if output_dir is None:
            output_dir = str(self.output_dir)
        os.makedirs(output_dir, exist_ok=True)
        
        # Save main results
        indices_file = os.path.join(output_dir, 'player1_index.csv')
        self.player_indices.to_csv(indices_file, index=False)
        logger.info(f"Saved player indices to {indices_file}")
        
        # Only CSV output is saved for this script.
    
    def generate_summary_report(self):
        """Generate a summary report of the index calculation"""
        logger.info("Generating summary report...")
        
        print("\n" + "="*80)
        print("NBA PLAYER INDEX CALCULATION - SUMMARY REPORT")
        print("="*80)
        
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
                print(f"{i:2d}. {player['player_name']:<25} Index: {player['index']:2.0f} (Age: {player['age_years']:.0f}, Pts: {player['pts']:.0f})")
        
        print("\n" + "="*80)


def main():
    """Main execution function"""
    logger.info("Starting NBA Player Index Calculation...")
    
    # Initialize calculator
    calculator = NBAPlayerIndexCalculator()
    
    try:
        # Load prepared data
        calculator.load_prepared_data()
        
        # Calculate indices
        calculator.calculate_player_indices()
        
        # Save results
        calculator.save_results()
        
        # Generate summary report
        calculator.generate_summary_report()
        
        logger.info("Index calculation completed successfully!")
        
    except Exception as e:
        logger.error(f"Index calculation failed: {e}")
        raise


if __name__ == "__main__":
    main()
