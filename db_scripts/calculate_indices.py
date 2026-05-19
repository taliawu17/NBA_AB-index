#!/usr/bin/env python3
"""
NBA Player AB-Index Calculation Script

AB-index k is the largest integer k such that some key-log game has age_years >= k
and points >= k. Equivalently, k = max over games of min(age_years, points).

Indices k < 18 are reported as NA (NBA cohort convention; no sub-draft-age index).

Export row: among games with age >= k and points >= k, pick highest points;
if tied, pick older age_years (paper tie-break).

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

# Report NA when computed k is below this (aligns with NBA minimum meaningful index).
AB_INDEX_MIN_VALID = 18


def prepare_top_games_for_index(df: pd.DataFrame) -> pd.DataFrame:
    """Top-games CSVs use clean_name; index scripts expect player_name."""
    out = df.copy()
    if "player_name" not in out.columns:
        if "clean_name" not in out.columns:
            raise ValueError("Missing player_name and clean_name columns")
        out["player_name"] = out["clean_name"]
    return out


def person_id_for_player(player_data: pd.DataFrame, ref_row: pd.Series | None = None) -> int | None:
    """personId (or person_id) for index export; prefer witness row when given."""
    for source in (ref_row, None):
        if source is not None:
            for col in ("personId", "person_id"):
                if col in source.index and pd.notna(source[col]):
                    val = pd.to_numeric(source[col], errors="coerce")
                    if pd.notna(val):
                        return int(val)
        else:
            for col in ("personId", "person_id"):
                if col not in player_data.columns:
                    continue
                vals = pd.to_numeric(player_data[col], errors="coerce").dropna()
                if not vals.empty:
                    return int(vals.iloc[0])
    return None


def compute_ab_index_threshold(
    g: pd.DataFrame,
    age_col: str = "age_years",
    pts_col: str = "points",
) -> Union[int, str]:
    """k = max over rows of min(age_years, points); k < AB_INDEX_MIN_VALID -> NA."""
    ages = pd.to_numeric(g[age_col], errors="coerce")
    pts = pd.to_numeric(g[pts_col], errors="coerce")
    valid = ages.notna() & pts.notna()
    if not valid.any():
        return "NA"
    m = np.minimum(ages[valid].to_numpy(dtype=float), pts[valid].to_numpy(dtype=float))
    mx = np.nanmax(m)
    if np.isnan(mx):
        return "NA"
    k = int(mx)
    if k < AB_INDEX_MIN_VALID:
        return "NA"
    return k


def select_witness_row_for_export(
    player_data: pd.DataFrame,
    player_index: Union[int, str],
    fallback: pd.Series,
    age_col: str = "age_years",
    pts_col: str = "points",
) -> pd.Series:
    """
    Witness set: age_years >= index and points >= index.
    Choose max points; tie-break by older age_years (higher).
    """
    if player_index == "NA" or (
        isinstance(player_index, str) and str(player_index).strip().upper() == "NA"
    ):
        return fallback
    if pts_col not in player_data.columns or age_col not in player_data.columns:
        return fallback
    ages = pd.to_numeric(player_data[age_col], errors="coerce")
    pts = pd.to_numeric(player_data[pts_col], errors="coerce")
    idx_int = int(player_index)
    mask = (ages >= idx_int) & (pts >= idx_int)
    cand = player_data.loc[mask].copy()
    if cand.empty:
        return fallback
    cand = cand.assign(_pts=pts.loc[cand.index], _age=ages.loc[cand.index])
    cand = cand.sort_values(
        by=["_pts", "_age"], ascending=[False, False], kind="mergesort"
    )
    row = cand.iloc[0]
    return row.drop(labels=[c for c in ("_pts", "_age") if c in row.index], errors="ignore")


def compute_index_from_pairs(pairs: List[Tuple[int, int]]) -> Union[int, str]:
    """k = max over pairs of min(age_years, points); k < AB_INDEX_MIN_VALID -> NA."""
    if not pairs:
        return "NA"
    k = int(max(min(age, pts) for age, pts in pairs))
    if k < AB_INDEX_MIN_VALID:
        return "NA"
    return k


def compute_indices_csv(
    input_csv: str,
    output_csv: str,
    id_col: str = "id",
    age_col: str = "age_years",
    pts_col: str = "points",
) -> None:
    """
    Read input CSV with columns [id_col, age_col, pts_col],
    compute the index per individual, and write results to output_csv.
    The output has columns [id_col, index].
    """
    df = pd.read_csv(input_csv)

    def index_for_group(g: pd.DataFrame) -> Union[int, str]:
        return compute_ab_index_threshold(g, age_col, pts_col)

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
        
    def load_prepared_data(self):
        """Load the prepared regular season data"""
        logger.info("Loading prepared regular season data...")
        
        try:
            # Load the prepared regular season data
            data_file = OUTPUT_DIR / "top2_games_per_season_with_birthdate - Copy.csv"
            if not os.path.exists(data_file):
                raise FileNotFoundError(f"Prepared data file not found: {data_file}")
            
            self.game_logs = pd.read_csv(data_file)
            logger.info(f"Loaded {len(self.game_logs):,} regular season records")
            logger.info(f"Unique players: {self.game_logs['player_name'].nunique():,}")
            
            # Check required columns
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
        
        # Filter out records with invalid age data
        # Also filter out impossible ages (under 18 for NBA players)
        valid_data = self.game_logs[
            self.game_logs['age_years'].notna() & 
            self.game_logs['points'].notna() &
            (self.game_logs['age_years'] >= 18)  # NBA players must be at least 18
        ].copy()
        
        logger.info(f"Using {len(valid_data):,} records with valid age and points data")
        
        # Calculate index for each player (max_k min(age, points) witness definition)
        def index_for_group(g: pd.DataFrame) -> Union[int, str]:
            return compute_ab_index_threshold(g, "age_years", "points")

        self.player_indices = (
            valid_data.groupby('player_name', sort=False)
            .apply(index_for_group)
            .reset_index(name="index")
        )
        
        # Add detailed information for each player's index calculation
        detailed_info = []
        
        for player_name in self.player_indices['player_name']:
            player_data = valid_data[valid_data['player_name'] == player_name].copy()
            player_index = self.player_indices[self.player_indices['player_name'] == player_name]['index'].iloc[0]
            
            if player_index != "NA":
                fallback = player_data.sort_values(
                    "points", ascending=False, kind="mergesort"
                ).iloc[0]
                max_game = select_witness_row_for_export(
                    player_data, player_index, fallback, "age_years", "points"
                )

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
            else:
                # For NA cases, add basic info
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
    
    def save_results(self, output_dir: str = str(OUTPUT_DIR)):
        """Save the calculated indices to files"""
        logger.info("Saving index calculation results...")
        
        if self.player_indices is None:
            raise ValueError("No indices calculated. Call calculate_player_indices() first.")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Save main results
        indices_file = os.path.join(output_dir, 'player_indices_20260204.csv')
        self.player_indices.to_csv(indices_file, index=False)
        logger.info(f"Saved player indices to {indices_file}")
        
        # Save sorted by index (descending)
        sorted_indices = self.player_indices.copy()
        valid_indices = sorted_indices[sorted_indices['index'] != 'NA'].copy()
        valid_indices['index'] = valid_indices['index'].astype(int)
        valid_indices['age_years'] = pd.to_numeric(valid_indices['age_years'], errors='coerce')
        valid_indices['age_days'] = pd.to_numeric(valid_indices['age_days'], errors='coerce')
        valid_indices['pts'] = pd.to_numeric(valid_indices['pts'], errors='coerce')
        valid_indices = valid_indices.sort_values(
            ['index', 'pts', 'age_years', 'age_days'],
            ascending=[False, False, False, False],
        )
        
        sorted_file = os.path.join(output_dir, 'player_indices_ranked_20260204.csv')
        valid_indices.to_csv(sorted_file, index=False)
        logger.info(f"Saved ranked player indices to {sorted_file}")
    
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
            top_players = valid_indices.sort_values(
                ['index', 'pts', 'age_years', 'age_days'],
                ascending=[False, False, False, False],
            ).head(20)
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
