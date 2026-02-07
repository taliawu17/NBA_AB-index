#!/usr/bin/env python3
"""
Simple runner script for NBA Player Index Calculation
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from calculate_indices import main

if __name__ == "__main__":
    print("NBA Player Index Calculation")
    print("=" * 50)
    print("This script will:")
    print("1. Load the prepared regular season data")
    print("2. Calculate index for each player using the rule:")
    print("   - Find first age_years (largest to smallest)")
    print("   - where points >= age_years")
    print("   - Return 'NA' if none found")
    print("3. Save results with player rankings")
    print("=" * 50)
    
    # Check if the prepared data exists
    if not os.path.exists("output/player_game_logs_regular_season.csv"):
        print("\n[ERROR] output/player_game_logs_regular_season.csv not found!")
        print("Please run the data preparation first:")
        print("python run_preparation.py")
        sys.exit(1)
    
    try:
        main()
        print("\n[SUCCESS] Index calculation completed!")
        print("\nOutput files:")
        print("- player_indices.csv: All players with indices")
        print("- player_indices_ranked.csv: Players ranked by index")
        print("- player_indices.xlsx: Excel format with multiple sheets")
        print("- player_indices.parquet: High-performance format")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("Please check the log file 'index_calculation.log' for details.")

