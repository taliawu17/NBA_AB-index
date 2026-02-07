#!/usr/bin/env python3
"""
Check specific missing players
"""

import pandas as pd

# Load data
stats = pd.read_csv('PlayerStatistics.csv')
target = pd.read_csv('target_player.csv')

# Check specific players
players_to_check = ['Al Attles', 'Anderson Varejão', 'Andrés Nocioni']

for player_name in players_to_check:
    print(f"\nChecking {player_name}:")
    
    # Check exact match
    exact_matches = stats[
        (stats['firstName'] + ' ' + stats['lastName'] == player_name)
    ]
    print(f"  Exact matches: {len(exact_matches)}")
    
    if len(exact_matches) == 0:
        # Try partial match
        first_name = player_name.split()[0]
        last_name = ' '.join(player_name.split()[1:])
        
        partial_matches = stats[
            (stats['firstName'].str.lower() == first_name.lower()) &
            (stats['lastName'].str.contains(last_name, case=False, na=False))
        ]
        print(f"  Partial matches: {len(partial_matches)}")
        
        if len(partial_matches) > 0:
            print(f"  Found names: {partial_matches['firstName'] + ' ' + partial_matches['lastName']}")
    
    # Check if player is in target list
    target_match = target[target['Clean Name'] == player_name]
    print(f"  In target list: {len(target_match) > 0}")
    if len(target_match) > 0:
        print(f"  Target Player Name: {target_match['Player Name'].iloc[0]}")
        print(f"  Target Birth Date: {target_match['Birth Date(TextToColumn)'].iloc[0]}")

