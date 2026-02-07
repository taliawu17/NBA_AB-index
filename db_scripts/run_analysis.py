#!/usr/bin/env python3
"""
Simple runner script for NBA Player Game Log Extraction
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nba_player_analysis import main

if __name__ == "__main__":
    print("NBA Player Game Log Extraction")
    print("=" * 40)
    print("This script will:")
    print("1. Load NBA player statistics data")
    print("2. Process 1,636 target players")
    print("3. Find highest scoring game per AGE for each player")
    print("4. Generate clean game log records for index calculation")
    print("5. Save results in multiple formats")
    print("=" * 40)
    print("Starting extraction...")
    
    try:
        main()
        print("\nExtraction completed! Check the 'output' directory for results.")
        print("\nOutput files:")
        print("- player_game_logs.csv: Combined game logs for all players")
        print("- player_detailed_logs.json: Detailed season-by-season data")
        print("- nba_player_data.xlsx: Excel workbook with game logs and statistics")
        print("- nba_player_data.parquet: High-performance format for analysis")
    except Exception as e:
        print(f"\nError: {e}")
        print("Please check the log file 'nba_analysis.log' for details.")
