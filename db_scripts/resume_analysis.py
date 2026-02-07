#!/usr/bin/env python3
"""
Resume script for NBA Player Game Log Extraction
Use this if the main process was interrupted
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nba_player_analysis import NBAPlayerGameLogExtractor

if __name__ == "__main__":
    print("NBA Player Game Log Extraction - RESUME MODE")
    print("=" * 50)
    print("This script will resume from the last checkpoint.")
    print("If no checkpoint exists, it will start fresh.")
    print("=" * 50)
    
    input("Press Enter to continue...")
    
    try:
        # Initialize extractor
        extractor = NBAPlayerGameLogExtractor()
        
        # Load data
        extractor.load_data()
        
        # Resume from checkpoint
        if extractor.resume_from_checkpoint():
            print(f"Resuming from checkpoint: {extractor.processed_count}/{extractor.total_players} players processed")
        else:
            print("No checkpoint found, starting fresh...")
        
        # Process remaining players
        extractor.process_all_players()
        
        # Save results
        extractor.save_game_logs("output")
        
        # Generate summary report
        extractor.generate_summary_report()
        
        print("\nExtraction completed! Check the 'output' directory for results.")
        
    except Exception as e:
        print(f"\nError: {e}")
        print("Please check the log file 'nba_analysis.log' for details.")

