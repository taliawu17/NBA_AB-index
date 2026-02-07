#!/usr/bin/env python3
"""
Runner script for NBA Game Log Extraction (Step 1)

This script runs the first step of the NBA analysis:
- Extract ALL game logs for target players (without age calculation)
- Handle player name differences and duplicates
- Save results for further processing
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extract_game_logs import main

if __name__ == "__main__":
    print("NBA Player Game Log Extraction - Step 1")
    print("=" * 50)
    print("This script will:")
    print("1. Load NBA player statistics data")
    print("2. Process 1,636 target players")
    print("3. Extract ALL game logs (without age calculation)")
    print("4. Handle player name differences and duplicates")
    print("5. Save results for further processing")
    print("=" * 50)
    print("Starting extraction...")
    
    try:
        main()
        print("\n[SUCCESS] Game log extraction completed successfully!")
        print("Check the 'output' directory for results:")
        print("- all_player_game_logs.csv: Combined game logs for all players")
        print("- duplicate_players.txt: Players with duplicate personIds")
        print("- all_player_game_logs.xlsx: Excel workbook with game logs")
        print("- all_player_game_logs.parquet: High-performance format")
    except Exception as e:
        print(f"\n[ERROR] Extraction failed: {e}")
        sys.exit(1)

