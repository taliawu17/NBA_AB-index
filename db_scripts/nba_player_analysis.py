#!/usr/bin/env python3
"""
NBA Player Game Log Extraction Script

This script processes NBA player statistics to:
1. Extract historical game logs by year for target players
2. Find highest scoring game per year for each player
3. Handle player uniqueness (same names, different players)
4. Generate clean game log records for index calculation

Author: NBA Analysis Team
Date: 2024
"""

import pandas as pd
import numpy as np
import json
import os
import pickle
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging
import signal
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
        logging.FileHandler('nba_analysis.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NBAPlayerGameLogExtractor:
    """Main class for extracting NBA player game logs"""
    
    def __init__(self, data_dir: str = ".", checkpoint_dir: str = "checkpoints"):
        """
        Initialize the extractor with data directory
        
        Args:
            data_dir: Directory containing CSV files
            checkpoint_dir: Directory for saving progress checkpoints
        """
        self.data_dir = data_dir
        self.checkpoint_dir = checkpoint_dir
        self.player_stats = None
        self.target_players = None
        self.player_info = None
        self.processed_data = {}
        self.processed_count = 0
        self.total_players = 0
        
        # Create checkpoint directory
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
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
            self.target_players = pd.read_csv(
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
    
    def _signal_handler(self, signum, frame):
        """Handle interruption signals gracefully"""
        logger.info(f"Received signal {signum}. Saving checkpoint and exiting gracefully...")
        self._save_checkpoint()
        logger.info("Checkpoint saved. You can resume later using resume_from_checkpoint()")
        sys.exit(0)
    
    def _save_checkpoint(self):
        """Save current progress to checkpoint file"""
        checkpoint_file = os.path.join(self.checkpoint_dir, 'progress.pkl')
        checkpoint_data = {
            'processed_data': self.processed_data,
            'processed_count': self.processed_count,
            'total_players': self.total_players,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            with open(checkpoint_file, 'wb') as f:
                pickle.dump(checkpoint_data, f)
            logger.info(f"Checkpoint saved: {self.processed_count}/{self.total_players} players processed")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def _load_checkpoint(self):
        """Load progress from checkpoint file"""
        checkpoint_file = os.path.join(self.checkpoint_dir, 'progress.pkl')
        
        if not os.path.exists(checkpoint_file):
            return False
        
        try:
            with open(checkpoint_file, 'rb') as f:
                checkpoint_data = pickle.load(f)
            
            self.processed_data = checkpoint_data['processed_data']
            self.processed_count = checkpoint_data['processed_count']
            self.total_players = checkpoint_data['total_players']
            
            logger.info(f"Loaded checkpoint: {self.processed_count}/{self.total_players} players already processed")
            logger.info(f"Checkpoint timestamp: {checkpoint_data['timestamp']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return False
    
    def resume_from_checkpoint(self):
        """Resume processing from checkpoint"""
        if self._load_checkpoint():
            logger.info("Resuming from checkpoint...")
            return True
        else:
            logger.info("No checkpoint found, starting fresh...")
            return False
    
    def handle_player_uniqueness(self) -> Dict[str, List[int]]:
        """
        Handle player uniqueness by creating a mapping of player names to personIds
        
        Returns:
            Dictionary mapping player names to list of personIds
        """
        logger.info("Handling player uniqueness...")

        # Build a personId lookup from Players.csv using name + birthdate
        players = self.player_info.copy()
        players["full_name"] = (players["firstName"].fillna("") + " " + players["lastName"].fillna("")).str.strip()
        players["birthdate_norm"] = pd.to_datetime(players["birthdate"], errors="coerce").dt.date
        players["full_name_norm"] = players["full_name"].map(self._normalize_name)
        players["last_name_norm"] = players["lastName"].fillna("").map(self._normalize_name)
        players["first_name_norm"] = players["firstName"].fillna("").map(self._normalize_name)

        # Create a mapping from target players to personIds
        player_name_mapping = {}
        missing_targets = []

        updated_target = self.target_players.copy()
        if "personId" not in updated_target.columns:
            updated_target["personId"] = None

        for idx, target_player in updated_target.iterrows():
            player_name = target_player["Player Name"]
            clean_name = target_player.get("Clean Name", player_name)
            birth_date_raw = target_player.get("Birth Date", None)
            if pd.isna(birth_date_raw):
                birth_date_raw = target_player.get("Birth Date(TextToColumn)", None)
            birth_date = pd.to_datetime(birth_date_raw, errors="coerce").date() if pd.notna(birth_date_raw) else None

            # First try: match by normalized name + birthdate in Players.csv
            name_norm = self._normalize_name(clean_name)
            exact_id_matches = players[
                (players["full_name_norm"] == name_norm) &
                (players["birthdate_norm"] == birth_date)
            ]["personId"].unique()

            if len(exact_id_matches) > 0:
                player_name_mapping[player_name] = list(exact_id_matches)
                updated_target.at[idx, "personId"] = exact_id_matches[0]
                logger.info(f"Found {len(exact_id_matches)} matches by name+birthdate for {player_name}")
                continue

            # Fallback: match by birthdate + last name (handles middle initials)
            target_last = name_norm.split()[-1] if name_norm else ""
            target_first = name_norm.split()[0] if name_norm else ""
            birthdate_matches = players[players["birthdate_norm"] == birth_date]
            birthdate_name_matches = birthdate_matches[
                (birthdate_matches["last_name_norm"] == target_last) &
                (birthdate_matches["first_name_norm"].str.startswith(target_first))
            ]["personId"].unique()

            if len(birthdate_name_matches) > 0:
                player_name_mapping[player_name] = list(birthdate_name_matches)
                updated_target.at[idx, "personId"] = birthdate_name_matches[0]
                logger.info(f"Found {len(birthdate_name_matches)} matches by birthdate+name for {player_name}")
                continue

            # Fallback: name-only match in Players.csv
            name_only_matches = players[
                (players["full_name_norm"] == name_norm)
            ]["personId"].unique()

            if len(name_only_matches) > 0:
                player_name_mapping[player_name] = list(name_only_matches)
                updated_target.at[idx, "personId"] = name_only_matches[0]
                logger.info(f"Found {len(name_only_matches)} matches by name-only for {player_name}")
            else:
                # If birthdate uniquely identifies a single player, accept it
                if len(birthdate_matches) == 1:
                    unique_id = birthdate_matches["personId"].iloc[0]
                    player_name_mapping[player_name] = [unique_id]
                    updated_target.at[idx, "personId"] = unique_id
                    logger.info(f"Matched by unique birthdate for {player_name}")
                    continue
                try:
                    logger.warning(f"No matches found for {player_name}")
                except UnicodeEncodeError:
                    logger.warning("No matches found for player (Unicode name)")
                player_name_mapping[player_name] = []
                missing_targets.append({
                    "Player Name": player_name,
                    "Clean Name": clean_name,
                    "Birth Date": birth_date_raw,
                })

        # Save missing targets list
        if missing_targets:
            missing_df = pd.DataFrame(missing_targets)
            output_dir = os.path.join(self.data_dir, "output")
            os.makedirs(output_dir, exist_ok=True)
            missing_path = os.path.join(output_dir, "missing_target_players.csv")
            missing_df.to_csv(missing_path, index=False)
            logger.info(f"Saved missing target players list to {missing_path}")

        # Persist updated target_player.csv with personId column
        target_path = os.path.join(self.data_dir, "target_player.csv")
        updated_target.to_csv(target_path, index=False)
        logger.info("Updated target_player.csv with personId column")

        # Log summary
        total_matches = sum(len(person_ids) for person_ids in player_name_mapping.values())
        logger.info(f"Total player matches found: {total_matches}")

        return player_name_mapping

    @staticmethod
    def _normalize_name(name: str) -> str:
        if not isinstance(name, str):
            return ""
        normalized = unicodedata.normalize("NFD", name)
        ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
        ascii_name = ascii_name.replace("*", "").strip()
        return " ".join(ascii_name.lower().split())
    
    def extract_player_game_logs(self, person_id: int) -> pd.DataFrame:
        """
        Extract game logs for a specific player
        
        Args:
            person_id: Player's personId
            
        Returns:
            DataFrame with player's game logs
        """
        player_games = self.player_stats[
            self.player_stats['personId'] == person_id
        ].copy()
        
        if len(player_games) == 0:
            return pd.DataFrame()
        
        # Extract year from gameDate
        player_games['year'] = player_games['gameDate'].dt.year
        
        # Sort by date
        player_games = player_games.sort_values('gameDate')
        
        return player_games
    
    def find_highest_scoring_games_by_age(self, player_games: pd.DataFrame) -> pd.DataFrame:
        """
        Find ALL highest scoring game(s) for each age (including ties)
        
        Args:
            player_games: DataFrame with player's game logs
            
        Returns:
            DataFrame with ALL highest scoring games per age
        """
        if len(player_games) == 0:
            return pd.DataFrame()
        
        # Calculate age for each game
        player_games = self._calculate_player_ages(player_games)
        
        # Group by age_years and find max points
        age_max = player_games.groupby('age_years')['points'].max().reset_index()
        age_max.rename(columns={'points': 'max_points'}, inplace=True)
        
        # Find ALL games with max points for each age
        highest_games = []
        
        for _, row in age_max.iterrows():
            age_years = row['age_years']
            max_points = row['max_points']
            
            # Get ALL games with max points at this age
            age_games = player_games[
                (player_games['age_years'] == age_years) & 
                (player_games['points'] == max_points)
            ]
            
            # Add ALL games with the highest score (not just the first one)
            for _, game in age_games.iterrows():
                best_game = game.copy()
                best_game['games_with_max_points'] = len(age_games)
                highest_games.append(best_game)
        
        return pd.DataFrame(highest_games)
    
    def _calculate_player_ages(self, player_games: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate precise age (XX-XXX format) for each game
        
        Args:
            player_games: DataFrame with player's game logs
            
        Returns:
            DataFrame with age information added
        """
        from datetime import datetime
        
        def last_birthday_on_or_before(asof_date, dob_date):
            """Return the most recent birthday on or before 'asof'.
            For a Feb 29 birthday in a non-leap year, use Feb 28."""
            def birthday_in_year(y):
                try:
                    return pd.Timestamp(y, dob_date.month, dob_date.day)
                except ValueError:
                    # Handles Feb 29 in non-leap years by using Feb 28.
                    return pd.Timestamp(y, 2, 28)

            lb = birthday_in_year(asof_date.year)
            if asof_date < lb:
                lb = birthday_in_year(asof_date.year - 1)
            return lb

        def age_xx_xxx(dob_date, asof_date):
            """Compute age as 'YY-DDD', where DDD is zero-padded to 3 digits."""
            if asof_date < dob_date:
                raise ValueError("As-of date is before date of birth.")
            last_bd = last_birthday_on_or_before(asof_date, dob_date)
            years = last_bd.year - dob_date.year
            days = (asof_date - last_bd).days
            return f"{years:02d}-{days:03d}", years, days
        
        # Convert dates
        player_games = player_games.copy()
        player_games['gameDate'] = pd.to_datetime(player_games['gameDate'])
        
        # Get player's birthday from target players
        target_players = pd.read_csv(os.path.join(self.data_dir, 'target_player.csv'))
        birthday_mapping = dict(zip(target_players['Player Name'], target_players['Birth Date']))
        
        # Calculate ages
        ages = []
        age_years = []
        age_days = []
        
        for idx, row in player_games.iterrows():
            try:
                # Get player name and find birthday
                player_name = row.get('player_name', '')
                birth_date_str = birthday_mapping.get(player_name)
                
                if pd.isna(birth_date_str):
                    ages.append(None)
                    age_years.append(None)
                    age_days.append(None)
                    continue
                
                birth_date = pd.to_datetime(birth_date_str)
                age_formatted, years, days = age_xx_xxx(birth_date, row['gameDate'])
                
                ages.append(age_formatted)
                age_years.append(years)
                age_days.append(days)
                
            except Exception as e:
                logger.warning(f"Error calculating age for {player_name}: {e}")
                ages.append(None)
                age_years.append(None)
                age_days.append(None)
        
        player_games['age_at_game'] = ages
        player_games['age_years'] = age_years
        player_games['age_days'] = age_days
        
        return player_games
    
    def process_all_players(self) -> None:
        """Process all target players and extract their highest scoring games by year"""
        logger.info("Processing all target players...")
        
        player_mapping = self.handle_player_uniqueness()
        
        # Set total players count
        self.total_players = len(player_mapping)
        
        # If resuming, skip already processed players
        if self.processed_count > 0:
            logger.info(f"Resuming from player {self.processed_count + 1}")
            player_items = list(player_mapping.items())[self.processed_count:]
        else:
            player_items = list(player_mapping.items())
        
        for player_name, person_ids in player_items:
            logger.info(f"Processing {player_name} ({self.processed_count + 1}/{self.total_players})")
            
            player_results = []
            
            for person_id in person_ids:
                # Extract game logs
                player_games = self.extract_player_game_logs(person_id)
                
                if len(player_games) == 0:
                    logger.warning(f"No games found for {player_name} (personId: {person_id})")
                    continue
                
                # Attach target name for birthday lookup before age calculations
                player_games = player_games.copy()
                player_games['player_name'] = player_name

                # Find highest scoring games by age
                highest_games = self.find_highest_scoring_games_by_age(player_games)
                
                if len(highest_games) > 0:
                    # Add player identification
                    highest_games['player_name'] = player_name
                    highest_games['person_id'] = person_id
                    
                    # Calculate additional metrics
                    highest_games['career_span'] = highest_games['year'].max() - highest_games['year'].min() + 1
                    highest_games['total_seasons'] = len(highest_games)
                    highest_games['avg_season_high'] = highest_games['points'].mean()
                    
                    player_results.append(highest_games)
                    
                    logger.info(f"  Found {len(highest_games)} age groups for {player_name} (personId: {person_id})")
                    logger.info(f"  Age range: {highest_games['age_years'].min()}-{highest_games['age_years'].max()}")
                    logger.info(f"  Highest single game: {highest_games['points'].max()} points")
            
            # Combine results for this player (in case of multiple personIds)
            if player_results:
                combined_results = pd.concat(player_results, ignore_index=True)
                self.processed_data[player_name] = combined_results
                self.processed_count += 1
            else:
                logger.warning(f"No valid data found for {player_name}")
                self.processed_count += 1
            
            # Save checkpoint every 50 players
            if self.processed_count % 50 == 0:
                self._save_checkpoint()
                logger.info(f"Checkpoint saved at player {self.processed_count}")
        
        logger.info(f"Processing completed! Successfully processed {self.processed_count} players")
    
    
    def save_game_logs(self, output_dir: str = "output") -> None:
        """Save extracted game logs to various formats"""
        logger.info("Saving game log results...")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Combine all player data into one DataFrame
        all_player_logs = []
        
        for player_name, player_data in self.processed_data.items():
            if len(player_data) == 0:
                continue
            
            # Add to combined logs
            all_player_logs.append(player_data)
        
        # Save combined game logs as CSV
        if all_player_logs:
            combined_logs = pd.concat(all_player_logs, ignore_index=True)
            logs_file = os.path.join(output_dir, 'player_game_logs.csv')
            combined_logs.to_csv(logs_file, index=False)
            logger.info(f"Saved combined game logs to {logs_file}")
            
            # Save as Excel workbook with multiple sheets
            excel_file = os.path.join(output_dir, 'nba_player_data.xlsx')
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                combined_logs.to_excel(writer, sheet_name='Game Logs', index=False)
                
                # Add a statistics sheet
                stats_data = {
                    'Metric': ['Total Players', 'Total Season Records', 'Date Range', 'Highest Single Game'],
                    'Value': [
                        len(self.processed_data),
                        len(combined_logs),
                        f"{combined_logs['year'].min()}-{combined_logs['year'].max()}",
                        f"{combined_logs['points'].max():.0f} points"
                    ]
                }
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_excel(writer, sheet_name='Statistics', index=False)
            
            logger.info(f"Saved Excel workbook to {excel_file}")
            
            # Save as Parquet for better performance
            parquet_file = os.path.join(output_dir, 'nba_player_data.parquet')
            combined_logs.to_parquet(parquet_file, index=False)
            logger.info(f"Saved Parquet file to {parquet_file}")
        
        # Save detailed player data as JSON
        detailed_file = os.path.join(output_dir, 'player_detailed_logs.json')
        detailed_data = {}
        
        for player_name, player_data in self.processed_data.items():
            if len(player_data) > 0:
                detailed_data[player_name] = {
                    'seasons': player_data.to_dict('records'),
                    'summary': {
                        'total_seasons': len(player_data),
                        'career_high': player_data['points'].max(),
                        'avg_season_high': player_data['points'].mean(),
                        'career_span': f"{player_data['year'].min()}-{player_data['year'].max()}"
                    }
                }
        
        with open(detailed_file, 'w') as f:
            json.dump(detailed_data, f, indent=2, default=str)
        logger.info(f"Saved detailed data to {detailed_file}")
        
        logger.info(f"Saved data for {len(self.processed_data)} players")
    
    def generate_summary_report(self) -> None:
        """Generate a summary report"""
        logger.info("Generating summary report...")
        
        print("\n" + "="*80)
        print("NBA PLAYER GAME LOG EXTRACTION - SUMMARY REPORT")
        print("="*80)
        
        total_players = len(self.processed_data)
        players_with_data = sum(1 for data in self.processed_data.values() if len(data) > 0)
        
        print(f"\nTotal Players Processed: {total_players}")
        print(f"Players with Game Data: {players_with_data}")
        
        if players_with_data > 0:
            # Calculate overall statistics
            all_logs = []
            for player_data in self.processed_data.values():
                if len(player_data) > 0:
                    all_logs.append(player_data)
            
            if all_logs:
                combined_logs = pd.concat(all_logs, ignore_index=True)
                
                print(f"\nOverall Statistics:")
                print("-" * 30)
                print(f"Total Age Group Records: {len(combined_logs)}")
                print(f"Average Age Groups per Player: {len(combined_logs) / players_with_data:.1f}")
                print(f"Highest Single Game: {combined_logs['points'].max():.0f} points")
                print(f"Average Age Group High: {combined_logs['points'].mean():.1f} points")
                print(f"Age Range: {combined_logs['age_years'].min()}-{combined_logs['age_years'].max()}")
                
                # Show top players by career high
                top_players = combined_logs.groupby('player_name')['points'].max().sort_values(ascending=False).head(10)
                print(f"\nTop 10 Players by Career High Points:")
                print("-" * 50)
                for i, (player, points) in enumerate(top_players.items(), 1):
                    print(f"{i:2d}. {player:<25} {points:3.0f} points")
        
        print("\n" + "="*80)


def main():
    """Main execution function"""
    logger.info("Starting NBA Player Game Log Extraction...")
    
    # Initialize extractor
    extractor = NBAPlayerGameLogExtractor()
    
    try:
        # Load data
        extractor.load_data()
        
        # Check if we should resume from checkpoint
        if extractor.resume_from_checkpoint():
            logger.info("Resuming from previous checkpoint...")
        else:
            logger.info("Starting fresh extraction...")
        
        # Process all players
        extractor.process_all_players()
        
        # Save results
        extractor.save_game_logs("output")
        
        # Generate summary report
        extractor.generate_summary_report()
        
        # Clean up checkpoint file after successful completion
        checkpoint_file = os.path.join(extractor.checkpoint_dir, 'progress.pkl')
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
            logger.info("Checkpoint file cleaned up after successful completion")
        
        logger.info("Game log extraction completed successfully!")
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise


if __name__ == "__main__":
    main()
