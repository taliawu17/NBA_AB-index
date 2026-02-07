#!/usr/bin/env python3
"""
Comprehensive analysis of missing players
"""

import pandas as pd

# Load data
stats = pd.read_csv('PlayerStatistics.csv')
target = pd.read_csv('target_player.csv')

# Check specific players with broader search
players_to_check = ['Al Attles', 'Anderson Varejão', 'Andrés Nocioni']

for player_name in players_to_check:
    print(f"\n=== Checking {player_name} ===")
    
    # Check exact match
    exact_matches = stats[
        (stats['firstName'] + ' ' + stats['lastName'] == player_name)
    ]
    print(f"Exact matches: {len(exact_matches)}")
    
    # Check last name only
    last_name = player_name.split()[-1]
    last_name_matches = stats[
        stats['lastName'].str.contains(last_name, case=False, na=False)
    ]
    print(f"Last name '{last_name}' matches: {len(last_name_matches)}")
    
    if len(last_name_matches) > 0:
        unique_names = (last_name_matches['firstName'] + ' ' + last_name_matches['lastName']).unique()
        print(f"Found names with '{last_name}': {list(unique_names)}")
    
    # Check if it's a very old player (pre-1970)
    target_match = target[target['Clean Name'] == player_name]
    if len(target_match) > 0:
        birth_date = target_match['Birth Date(TextToColumn)'].iloc[0]
        print(f"Birth date: {birth_date}")
        
        # Check if there are any games from very early years
        early_games = stats[stats['gameDate'].str.contains('1946|1947|1948|1949|1950', na=False)]
        print(f"Games from 1946-1950: {len(early_games)}")
        
        if len(early_games) > 0:
            early_players = (early_games['firstName'] + ' ' + early_games['lastName']).unique()
            print(f"Players from 1946-1950: {len(early_players)}")
            if player_name.split()[-1].lower() in [name.split()[-1].lower() for name in early_players]:
                print(f"Found potential early player with similar last name")

print("\n=== Summary ===")
print("These players are likely missing because:")
print("1. They played in very early NBA seasons (1946-1950) when data might be incomplete")
print("2. They have different name formats in the database")
print("3. They might be ABA players not included in NBA statistics")
print("4. They could be players with very short careers or minimal playing time")

