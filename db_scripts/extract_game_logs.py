#!/usr/bin/env python3
"""
NBA Player Game Log Extraction - Step 1: Extract All Game Logs

This script processes NBA player statistics to:
1. Extract ALL game logs for target players (without age calculation)
2. Handle player name differences between target_player.csv and PlayerStatistics.csv
3. Save duplicate player names to a text file for review
4. Add player ID to all extracted game logs
5. Use Clean Name from target_player.csv for consistency

Date: 2026
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging
import sys
import unicodedata

# Configure logging
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game_log_extraction.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NBAGameLogExtractor:
    """Main class for extracting NBA player game logs (Step 1)"""
    
    def __init__(self, data_dir: str = "."):
        """
        Initialize the extractor with data directory
        
        Args:
            data_dir: Directory containing CSV files
        """
        self.data_dir = data_dir
        self.player_stats = None
        self.target_players = None
        self.player_info = None
        self.extracted_logs = {}
        self.duplicate_players = []
        
    def load_data(self) -> None:
        """Load all required CSV files"""
        logger.info("Loading NBA data files...")
        
        try:
            # Load player statistics (main dataset)
            logger.info("Loading PlayerStatistics.csv...")
            self.player_stats = pd.read_csv(
                os.path.join(self.data_dir, 'PlayerStatistics.csv'),
                low_memory=False
            )
            logger.info(f"Loaded {len(self.player_stats):,} player statistics records")
            
            # Load target players list
            logger.info("Loading target_player.csv...")
            self.target_players = self._read_csv_with_fallback(
                os.path.join(self.data_dir, 'target_player.csv')
            )
            logger.info(f"Loaded {len(self.target_players)} target players")
            
            # Load player information for uniqueness handling
            logger.info("Loading Players.csv...")
            self.player_info = pd.read_csv(
                os.path.join(self.data_dir, 'Players.csv')
            )
            logger.info(f"Loaded {len(self.player_info)} player records")
            
            # Convert gameDate to datetime
            self.player_stats['gameDate'] = pd.to_datetime(self.player_stats['gameDate'])
            
            logger.info("Data loading completed successfully!")
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise

    @staticmethod
    def _read_csv_with_fallback(path: str) -> pd.DataFrame:
        """Read CSV with encoding fallback for legacy files."""
        try:
            return pd.read_csv(path)
        except UnicodeDecodeError:
            return pd.read_csv(path, encoding="latin1")
    
    def handle_player_uniqueness(self) -> Dict[str, List[int]]:
        """
        Handle player uniqueness by creating a mapping of clean names to personIds
        
        Returns:
            Dictionary mapping clean names to list of personIds
        """
        logger.info("Handling player uniqueness...")
        
        # Create a mapping from target players to personIds
        player_name_mapping = {}
        
        for _, target_player in self.target_players.iterrows():
            player_name = target_player.get('Player Name')
            clean_name = target_player.get('Clean Name', player_name)
            person_id = target_player.get('personId')

            if pd.notna(person_id):
                player_name_mapping[clean_name] = [int(person_id)]
                continue
            
            # Find matching players in the main dataset using clean name
            # Try exact match first, then fuzzy matching
            exact_matches = self.player_stats[
                (self.player_stats['firstName'] + ' ' + self.player_stats['lastName'] == clean_name)
            ]['personId'].unique()
            
            if len(exact_matches) > 0:
                player_name_mapping[clean_name] = list(exact_matches)
                logger.info(f"Found {len(exact_matches)} exact matches for {clean_name}")
            else:
                # Try partial matching (remove asterisks and other special characters)
                clean_player_name = clean_name.replace('*', '').strip()
                first_name = clean_player_name.split()[0]
                last_name = ' '.join(clean_player_name.split()[1:])
                
                # More precise matching: exact first name match, last name contains
                partial_matches = self.player_stats[
                    (self.player_stats['firstName'].str.lower() == first_name.lower()) &
                    (self.player_stats['lastName'].str.contains(last_name, case=False, na=False))
                ]['personId'].unique()
                
                if len(partial_matches) > 0:
                    player_name_mapping[clean_name] = list(partial_matches)
                    logger.info(f"Found {len(partial_matches)} partial matches for {clean_name}")
                else:
                    try:
                        logger.warning(f"No matches found for {clean_name}")
                    except UnicodeEncodeError:
                        logger.warning(f"No matches found for player (Unicode name)")
                    player_name_mapping[clean_name] = []
        
        # Log summary
        total_matches = sum(len(person_ids) for person_ids in player_name_mapping.values())
        logger.info(f"Total player matches found: {total_matches}")
        
        return player_name_mapping
    
    def extract_player_game_logs(self, person_id: int, clean_name: str) -> pd.DataFrame:
        """
        Extract game logs for a specific player
        
        Args:
            person_id: Player's personId
            clean_name: Player's clean name
            
        Returns:
            DataFrame with player's game logs
        """
        player_games = self.player_stats[
            self.player_stats['personId'] == person_id
        ].copy()
        
        if len(player_games) == 0:
            return pd.DataFrame()
        
        # Add player identification
        player_games['clean_name'] = clean_name
        player_games['person_id'] = person_id
        
        # Extract year from gameDate
        player_games['year'] = player_games['gameDate'].dt.year
        
        # Sort by date
        player_games = player_games.sort_values('gameDate')
        
        return player_games
    
    def process_all_players(self) -> None:
        """Process all target players and extract their game logs"""
        logger.info("Processing all target players...")
        
        player_mapping = self.handle_player_uniqueness()
        
        # Track duplicate players
        self.duplicate_players = []
        
        for clean_name, person_ids in player_mapping.items():
            logger.info(f"Processing {clean_name} ({len(person_ids)} personIds)")
            
            player_results = []
            
            for person_id in person_ids:
                # Extract game logs
                player_games = self.extract_player_game_logs(person_id, clean_name)
                
                if len(player_games) == 0:
                    logger.warning(f"No games found for {clean_name} (personId: {person_id})")
                    continue
                
                player_results.append(player_games)
                
                logger.info(f"  Found {len(player_games)} games for {clean_name} (personId: {person_id})")
            
            # Combine results for this player (in case of multiple personIds)
            if player_results:
                combined_results = pd.concat(player_results, ignore_index=True)
                self.extracted_logs[clean_name] = combined_results
                
                # Track if this player has multiple personIds (duplicates)
                if len(person_ids) > 1:
                    self.duplicate_players.append({
                        'clean_name': clean_name,
                        'person_ids': person_ids,
                        'total_games': len(combined_results)
                    })
                    logger.info(f"  DUPLICATE: {clean_name} has {len(person_ids)} personIds")
            else:
                logger.warning(f"No valid data found for {clean_name}")
        
        logger.info(f"Processing completed! Successfully processed {len(self.extracted_logs)} players")
        logger.info(f"Found {len(self.duplicate_players)} players with duplicate personIds")
    
    def save_duplicate_players(self, output_dir: str = "output") -> None:
        """Save duplicate player information to a text file"""
        logger.info("Saving duplicate player information...")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Save duplicate players to text file
        duplicate_file = os.path.join(output_dir, 'duplicate_players.txt')
        
        with open(duplicate_file, 'w', encoding='utf-8') as f:
            f.write("NBA Player Duplicate Analysis\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Total players with duplicate personIds: {len(self.duplicate_players)}\n\n")
            
            for dup in self.duplicate_players:
                f.write(f"Player: {dup['clean_name']}\n")
                f.write(f"PersonIds: {dup['person_ids']}\n")
                f.write(f"Total Games: {dup['total_games']}\n")
                f.write("-" * 30 + "\n")
        
        logger.info(f"Saved duplicate player information to {duplicate_file}")
    
    def save_game_logs(self, output_dir: str = "output") -> None:
        """Save extracted game logs to various formats"""
        logger.info("Saving game log results...")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Combine all player data into one DataFrame
        all_player_logs = []
        
        for clean_name, player_data in self.extracted_logs.items():
            if len(player_data) == 0:
                continue
            
            # Add to combined logs
            all_player_logs.append(player_data)
        
        # Save combined game logs as CSV
        if all_player_logs:
            combined_logs = pd.concat(all_player_logs, ignore_index=True)
            logs_file = os.path.join(output_dir, 'all_player_game_logs.csv')
            combined_logs.to_csv(logs_file, index=False)
            logger.info(f"Saved combined game logs to {logs_file}")

            # Save regular season only
            regular_season = combined_logs[combined_logs['gameType'] == 'Regular Season'].copy()
            regular_file = os.path.join(output_dir, 'all_player_game_logs_regular_season.csv')
            regular_season.to_csv(regular_file, index=False)
            logger.info(f"Saved regular season logs to {regular_file}")
            
            # Save as Excel workbook with multiple sheets (skip if too large)
            if len(combined_logs) <= 1_000_000:
                excel_file = os.path.join(output_dir, 'all_player_game_logs.xlsx')
                try:
                    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                        combined_logs.to_excel(writer, sheet_name='All Game Logs', index=False)
                        
                        # Add a statistics sheet
                        stats_data = {
                            'Metric': ['Total Players', 'Total Game Records', 'Date Range', 'Highest Single Game'],
                            'Value': [
                                len(self.extracted_logs),
                                len(combined_logs),
                                f"{combined_logs['year'].min()}-{combined_logs['year'].max()}",
                                f"{combined_logs['points'].max():.0f} points"
                            ]
                        }
                        stats_df = pd.DataFrame(stats_data)
                        stats_df.to_excel(writer, sheet_name='Statistics', index=False)
                    logger.info(f"Saved Excel workbook to {excel_file}")
                except Exception as exc:
                    logger.warning(f"Skipped Excel export: {exc}")
            else:
                logger.warning("Skipped Excel export: too many rows for Excel limits")
            
            # Save as Parquet for better performance
            parquet_file = os.path.join(output_dir, 'all_player_game_logs.parquet')
            combined_logs.to_parquet(parquet_file, index=False)
            logger.info(f"Saved Parquet file to {parquet_file}")
        
        logger.info(f"Saved data for {len(self.extracted_logs)} players")
    
    def generate_summary_report(self) -> None:
        """Generate a summary report"""
        logger.info("Generating summary report...")
        
        print("\n" + "="*80)
        print("NBA PLAYER GAME LOG EXTRACTION - SUMMARY REPORT")
        print("="*80)
        
        total_players = len(self.extracted_logs)
        players_with_data = sum(1 for data in self.extracted_logs.values() if len(data) > 0)
        
        print(f"\nTotal Players Processed: {total_players}")
        print(f"Players with Game Data: {players_with_data}")
        print(f"Players with Duplicate PersonIds: {len(self.duplicate_players)}")
        
        if players_with_data > 0:
            # Calculate overall statistics
            all_logs = []
            for player_data in self.extracted_logs.values():
                if len(player_data) > 0:
                    all_logs.append(player_data)
            
            if all_logs:
                combined_logs = pd.concat(all_logs, ignore_index=True)
                
                print(f"\nOverall Statistics:")
                print("-" * 30)
                print(f"Total Game Records: {len(combined_logs)}")
                print(f"Average Games per Player: {len(combined_logs) / players_with_data:.1f}")
                print(f"Highest Single Game: {combined_logs['points'].max():.0f} points")
                print(f"Average Game Points: {combined_logs['points'].mean():.1f} points")
                print(f"Date Range: {combined_logs['year'].min()}-{combined_logs['year'].max()}")
                
                # Show top players by career high
                top_players = combined_logs.groupby('clean_name')['points'].max().sort_values(ascending=False).head(10)
                print(f"\nTop 10 Players by Career High Points:")
                print("-" * 50)
                for i, (player, points) in enumerate(top_players.items(), 1):
                    print(f"{i:2d}. {player:<25} {points:3.0f} points")
        
        print("\n" + "="*80)


def main():
    """Main execution function"""
    logger.info("Starting NBA Player Game Log Extraction (Step 1)...")
    
    # Initialize extractor
    extractor = NBAGameLogExtractor()
    
    try:
        # Load data
        extractor.load_data()
        
        # Process all players
        extractor.process_all_players()
        
        # Save results
        extractor.save_game_logs("output")
        
        # Save duplicate player information
        extractor.save_duplicate_players("output")
        
        # Generate summary report
        extractor.generate_summary_report()
        
        logger.info("Game log extraction completed successfully!")
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise


if __name__ == "__main__":
    main()

