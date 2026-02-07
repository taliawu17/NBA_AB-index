#!/usr/bin/env python3
"""
Analyze missing players between target list and extracted game logs
"""

import pandas as pd

def analyze_missing_players():
    # Load target players
    target = pd.read_csv('target_player.csv')
    print(f"Target players: {len(target)}")
    
    # Load game logs
    game_logs = pd.read_csv('output/all_player_game_logs.csv')
    print(f"Players with game logs: {game_logs['clean_name'].nunique()}")
    
    # Get sets of names
    target_names = set(target['Clean Name'])
    game_log_names = set(game_logs['clean_name'])
    
    # Find missing players
    missing = target_names - game_log_names
    print(f"Missing players: {len(missing)}")
    
    print("\nFirst 10 missing players:")
    for i, name in enumerate(sorted(missing)):
        print(f"{i+1}. {name}")
    
    # Check a few specific examples
    print("\nChecking specific missing players:")
    for name in sorted(missing)[:3]:
        # Check if they exist in PlayerStatistics.csv
        player_stats = pd.read_csv('PlayerStatistics.csv')
        matches = player_stats[
            (player_stats['firstName'] + ' ' + player_stats['lastName'] == name)
        ]
        print(f"\n{name}:")
        print(f"  Matches in PlayerStatistics: {len(matches)}")
        if len(matches) > 0:
            print(f"  PersonIds: {matches['personId'].unique()}")
            print(f"  Games: {len(matches)}")

if __name__ == "__main__":
    analyze_missing_players()

