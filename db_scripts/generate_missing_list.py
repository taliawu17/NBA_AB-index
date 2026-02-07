#!/usr/bin/env python3
"""
Generate comprehensive list of missing players
"""

import pandas as pd
import unicodedata

def normalize_name(name):
    """Normalize name by removing accents and special characters"""
    # Remove accents
    normalized = unicodedata.normalize('NFD', name)
    ascii_name = normalized.encode('ascii', 'ignore').decode('ascii')
    # Remove asterisks and extra spaces
    ascii_name = ascii_name.replace('*', '').strip()
    return ascii_name.lower()

def analyze_missing_players():
    # Load data
    target = pd.read_csv('target_player.csv')
    game_logs = pd.read_csv('output/all_player_game_logs.csv')
    stats = pd.read_csv('PlayerStatistics.csv')
    
    print(f"Target players: {len(target)}")
    print(f"Players with game logs: {game_logs['clean_name'].nunique()}")
    
    # Get sets of names
    target_names = set(target['Clean Name'])
    game_log_names = set(game_logs['clean_name'])
    
    # Find missing players
    missing = target_names - game_log_names
    print(f"Missing players: {len(missing)}")
    
    # Create detailed analysis
    missing_analysis = []
    
    for player_name in sorted(missing):
        # Get target player info
        target_info = target[target['Clean Name'] == player_name]
        if len(target_info) > 0:
            target_player_name = target_info['Player Name'].iloc[0]
            birth_date = target_info['Birth Date(TextToColumn)'].iloc[0]
        else:
            target_player_name = "Unknown"
            birth_date = "Unknown"
        
        # Check exact match in stats
        exact_matches = stats[
            (stats['firstName'] + ' ' + stats['lastName'] == player_name)
        ]
        
        # Check normalized match
        normalized_player = normalize_name(player_name)
        normalized_matches = stats[
            stats.apply(lambda row: normalize_name(row['firstName'] + ' ' + row['lastName']) == normalized_player, axis=1)
        ]
        
        # Check last name only
        last_name = player_name.split()[-1]
        last_name_matches = stats[
            stats['lastName'].str.contains(last_name, case=False, na=False)
        ]
        
        # Check first name only
        first_name = player_name.split()[0]
        first_name_matches = stats[
            stats['firstName'].str.contains(first_name, case=False, na=False)
        ]
        
        missing_analysis.append({
            'Clean Name': player_name,
            'Target Player Name': target_player_name,
            'Birth Date': birth_date,
            'Exact Matches': len(exact_matches),
            'Normalized Matches': len(normalized_matches),
            'Last Name Matches': len(last_name_matches),
            'First Name Matches': len(first_name_matches),
            'Potential Matches': []
        })
        
        # Find potential matches
        if len(last_name_matches) > 0:
            potential_names = (last_name_matches['firstName'] + ' ' + last_name_matches['lastName']).unique()
            missing_analysis[-1]['Potential Matches'] = list(potential_names)[:5]  # Limit to 5
    
    # Convert to DataFrame and save
    missing_df = pd.DataFrame(missing_analysis)
    
    # Save to CSV
    missing_df.to_csv('output/missing_players_analysis.csv', index=False)
    print(f"\nSaved detailed analysis to: output/missing_players_analysis.csv")
    
    # Print summary
    print(f"\n=== MISSING PLAYERS SUMMARY ===")
    print(f"Total missing: {len(missing_df)}")
    
    # Categorize by match type
    exact_match_count = len(missing_df[missing_df['Exact Matches'] > 0])
    normalized_match_count = len(missing_df[missing_df['Normalized Matches'] > 0])
    last_name_match_count = len(missing_df[missing_df['Last Name Matches'] > 0])
    no_match_count = len(missing_df[missing_df['Last Name Matches'] == 0])
    
    print(f"Players with exact matches: {exact_match_count}")
    print(f"Players with normalized matches: {normalized_match_count}")
    print(f"Players with last name matches: {last_name_match_count}")
    print(f"Players with no matches at all: {no_match_count}")
    
    # Show first 10 missing players
    print(f"\n=== FIRST 10 MISSING PLAYERS ===")
    for i, row in missing_df.head(10).iterrows():
        print(f"{i+1}. {row['Clean Name']} (Birth: {row['Birth Date']})")
        if row['Potential Matches']:
            print(f"   Potential matches: {', '.join(row['Potential Matches'])}")
        else:
            print(f"   No potential matches found")
    
    return missing_df

if __name__ == "__main__":
    missing_df = analyze_missing_players()

