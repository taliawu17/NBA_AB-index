#!/usr/bin/env python3
"""
Simple runner script for NBA Data Preparation
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prepare_data import main

if __name__ == "__main__":
    print("NBA Data Preparation")
    print("=" * 40)
    print("This script will:")
    print("1. Load the extracted game logs from output/player_game_logs.csv")
    print("2. Filter to regular season data only (remove playoffs)")
    print("3. Add birthday information from target_player.csv")
    print("4. Calculate age at game time")
    print("5. Save cleaned data to new files")
    print("=" * 40)
    
    # Check if the main extraction output exists
    if not os.path.exists("output/player_game_logs.csv"):
        print("\n[ERROR] output/player_game_logs.csv not found!")
        print("Please run the main extraction first:")
        print("python run_analysis.py")
        sys.exit(1)
    
    print("Starting data preparation...")
    
    try:
        main()
        print("\n[SUCCESS] Data preparation completed!")
        print("\nOutput files:")
        print("- player_game_logs_regular_season.csv: Regular season data with birthdays")
        print("- player_game_logs_regular_season.xlsx: Excel format with summary")
        print("- player_game_logs_regular_season.parquet: High-performance format")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        print("Please check the log file 'data_preparation.log' for details.")
