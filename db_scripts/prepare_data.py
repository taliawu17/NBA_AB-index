#!/usr/bin/env python3
"""
NBA Data Preparation Script

This script processes the extracted game logs to:
1. Filter only regular season data (remove playoff games)
2. Add birthday information from target player list
3. Save the cleaned data to a new CSV file

Author: NBA Analysis Team
Date: 2024
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_preparation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NBADataPreparator:
    """Class for preparing NBA game log data"""
    
    def __init__(self, data_dir: str = "."):
        """
        Initialize the preparator
        
        Args:
            data_dir: Directory containing the data files
        """
        self.data_dir = data_dir
        self.game_logs = None
        self.target_players = None
        self.prepared_data = None
        
    def load_data(self):
        """Load the extracted game logs and target player data"""
        logger.info("Loading extracted data...")
        
        try:
            # Load the extracted game logs
            logs_file = os.path.join(self.data_dir, 'output', 'player_game_logs.csv')
            if not os.path.exists(logs_file):
                raise FileNotFoundError(f"Game logs file not found: {logs_file}")
            
            self.game_logs = pd.read_csv(logs_file)
            logger.info(f"Loaded {len(self.game_logs):,} game log records")
            
            # Load target players for birthday information
            target_file = os.path.join(self.data_dir, 'target_player.csv')
            if not os.path.exists(target_file):
                raise FileNotFoundError(f"Target players file not found: {target_file}")
            
            self.target_players = pd.read_csv(target_file)
            logger.info(f"Loaded {len(self.target_players)} target players")
            
            logger.info("Data loading completed successfully!")
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
    
    def filter_regular_season(self):
        """Filter to only include regular season games"""
        logger.info("Filtering regular season data...")
        
        if self.game_logs is None:
            raise ValueError("Game logs not loaded. Call load_data() first.")
        
        # Check what game types exist
        game_types = self.game_logs['gameType'].value_counts()
        logger.info(f"Game types found: {dict(game_types)}")
        
        # Filter for regular season only
        original_count = len(self.game_logs)
        self.game_logs = self.game_logs[
            self.game_logs['gameType'] == 'Regular Season'
        ].copy()
        
        filtered_count = len(self.game_logs)
        removed_count = original_count - filtered_count
        
        logger.info(f"Filtered to regular season: {filtered_count:,} records")
        logger.info(f"Removed playoff/preseason games: {removed_count:,} records")
        
        if filtered_count == 0:
            logger.warning("No regular season data found!")
        else:
            logger.info(f"Regular season data percentage: {filtered_count/original_count*100:.1f}%")
    
    def validate_age_data(self):
        """Validate that age data is present from the extraction"""
        logger.info("Validating age data from extraction...")
        
        if self.game_logs is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        # Check if age columns exist
        required_age_columns = ['age_at_game', 'age_years', 'age_days']
        missing_columns = [col for col in required_age_columns if col not in self.game_logs.columns]
        
        if missing_columns:
            logger.error(f"Missing age columns: {missing_columns}")
            logger.error("Age data should be calculated during extraction. Please re-run the extraction script.")
            raise ValueError(f"Missing age columns: {missing_columns}")
        
        # Count records with age data
        records_with_age = self.game_logs['age_years'].notna().sum()
        total_records = len(self.game_logs)
        
        logger.info(f"Age data validation: {records_with_age:,} records have age data")
        logger.info(f"Age coverage: {records_with_age/total_records*100:.1f}%")
        
        # Show age statistics
        if records_with_age > 0:
            age_years_data = self.game_logs[self.game_logs['age_years'].notna()]['age_years']
            age_days_data = self.game_logs[self.game_logs['age_days'].notna()]['age_days']
            logger.info(f"Age statistics: Min={age_years_data.min():.0f}-{age_days_data.min():.0f}, Max={age_years_data.max():.0f}-{age_days_data.max():.0f}, Mean={age_years_data.mean():.0f}-{age_days_data.mean():.0f}")
        else:
            logger.warning("No valid age data found")
        
        # Add birth_date column if missing (for compatibility with existing code)
        if 'birth_date' not in self.game_logs.columns:
            logger.info("Adding birth_date column for compatibility...")
            # Create a dummy birth_date column (will be filled from target players if needed)
            self.game_logs['birth_date'] = None
    
    def save_prepared_data(self, output_file: str = "output/player_game_logs_regular_season.csv"):
        """Save the prepared data to a new CSV file"""
        logger.info("Saving prepared data...")
        
        if self.game_logs is None:
            raise ValueError("No data to save. Run preparation steps first.")
        
        # Ensure output directory exists
        import os
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Save to CSV
        self.game_logs.to_csv(output_file, index=False)
        logger.info(f"Saved prepared data to {output_file}")
        
        # Also save as Excel for easy viewing
        excel_file = output_file.replace('.csv', '.xlsx')
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            self.game_logs.to_excel(writer, sheet_name='Regular Season Data', index=False)
            
            # Add summary statistics
            summary_data = {
                'Metric': [
                    'Total Records',
                    'Unique Players',
                    'Date Range',
                    'Records with Birthday',
                    'Average Age (Years)',
                    'Average Age (Days)',
                    'Youngest Player Age',
                    'Oldest Player Age'
                ],
                'Value': [
                    len(self.game_logs),
                    self.game_logs['player_name'].nunique(),
                    f"{self.game_logs['year'].min()}-{self.game_logs['year'].max()}",
                    self.game_logs['birth_date'].notna().sum(),
                    f"{self.game_logs['age_years'].mean():.1f}" if self.game_logs['age_years'].notna().sum() > 0 else "N/A",
                    f"{self.game_logs['age_days'].mean():.1f}" if self.game_logs['age_days'].notna().sum() > 0 else "N/A",
                    f"{self.game_logs['age_years'].min():.0f}-{self.game_logs['age_days'].min():.0f}" if self.game_logs['age_years'].notna().sum() > 0 else "N/A",
                    f"{self.game_logs['age_years'].max():.0f}-{self.game_logs['age_days'].max():.0f}" if self.game_logs['age_years'].notna().sum() > 0 else "N/A"
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        logger.info(f"Saved Excel file to {excel_file}")
        
        # Save as Parquet for performance
        parquet_file = output_file.replace('.csv', '.parquet')
        self.game_logs.to_parquet(parquet_file, index=False)
        logger.info(f"Saved Parquet file to {parquet_file}")
    
    def generate_summary_report(self):
        """Generate a summary report of the prepared data"""
        logger.info("Generating summary report...")
        
        print("\n" + "="*80)
        print("NBA DATA PREPARATION - SUMMARY REPORT")
        print("="*80)
        
        if self.game_logs is None:
            print("No data prepared yet.")
            return
        
        print(f"\nData Overview:")
        print("-" * 30)
        print(f"Total Records: {len(self.game_logs):,}")
        print(f"Unique Players: {self.game_logs['player_name'].nunique():,}")
        print(f"Date Range: {self.game_logs['year'].min()}-{self.game_logs['year'].max()}")
        print(f"Seasons Covered: {self.game_logs['year'].nunique()}")
        
        print(f"\nAge-Based Data:")
        print("-" * 30)
        records_with_age = self.game_logs['age_years'].notna().sum()
        print(f"Records with Age Data: {records_with_age:,}")
        print(f"Coverage: {records_with_age/len(self.game_logs)*100:.1f}%")
        
        if records_with_age > 0:
            age_years_data = self.game_logs[self.game_logs['age_years'].notna()]['age_years']
            age_days_data = self.game_logs[self.game_logs['age_days'].notna()]['age_days']
            print(f"Age Range: {age_years_data.min():.0f}-{age_days_data.min():.0f} to {age_years_data.max():.0f}-{age_days_data.max():.0f}")
            print(f"Average Age: {age_years_data.mean():.0f}-{age_days_data.mean():.0f}")
            print(f"Unique Age Groups: {self.game_logs['age_years'].nunique()}")
        else:
            print("Age Range: No valid age data")
            print("Average Age: No valid age data")
        
        print(f"\nTop 10 Players by Career High (Regular Season):")
        print("-" * 50)
        top_players = self.game_logs.groupby('player_name')['points'].max().sort_values(ascending=False).head(10)
        for i, (player, points) in enumerate(top_players.items(), 1):
            print(f"{i:2d}. {player:<25} {points:3.0f} points")
        
        print("\n" + "="*80)


def main():
    """Main execution function"""
    logger.info("Starting NBA Data Preparation...")
    
    # Initialize preparator
    preparator = NBADataPreparator()
    
    try:
        # Load data
        preparator.load_data()
        
        # Filter regular season data
        preparator.filter_regular_season()
        
        # Validate age data (should be calculated during extraction)
        preparator.validate_age_data()
        
        # Save prepared data
        preparator.save_prepared_data()
        
        # Generate summary report
        preparator.generate_summary_report()
        
        logger.info("Data preparation completed successfully!")
        
    except Exception as e:
        logger.error(f"Data preparation failed: {e}")
        raise


if __name__ == "__main__":
    main()
