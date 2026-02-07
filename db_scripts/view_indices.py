#!/usr/bin/env python3
"""
NBA Index Results Viewer - View the calculated player indices
"""

import pandas as pd
import os
import sys

def view_index_results():
    """View summary of index calculation results"""
    output_dir = "output"
    
    if not os.path.exists(output_dir):
        print("[ERROR] Output directory not found. Run the index calculation first.")
        return
    
    print("NBA Player Index Results Summary")
    print("=" * 50)
    
    # Check what files exist
    files = os.listdir(output_dir)
    index_files = [f for f in files if 'indices' in f]
    print(f"Index files: {index_files}")
    print()
    
    # Load index results
    indices_file = os.path.join(output_dir, 'player_indices.csv')
    if os.path.exists(indices_file):
        data = pd.read_csv(indices_file)
        print(f"[SUCCESS] Index Results Summary ({len(data):,} players):")
        
        # Basic statistics
        valid_indices = data[data['index'].notna()].copy()
        if len(valid_indices) > 0:
            valid_indices['index'] = valid_indices['index'].astype(int)
        
        print(f"   - Total players: {len(data):,}")
        print(f"   - Players with valid index: {len(valid_indices):,}")
        print(f"   - Players with NA index: {len(data) - len(valid_indices):,}")
        
        if len(valid_indices) > 0:
            print(f"   - Index range: {valid_indices['index'].min()}-{valid_indices['index'].max()}")
            print(f"   - Average index: {valid_indices['index'].mean():.1f}")
            print(f"   - Median index: {valid_indices['index'].median():.1f}")
        
        print()
        
        # Top players by index
        if len(valid_indices) > 0:
            top_players = valid_indices.sort_values('index', ascending=False).head(15)
            print("Top 15 Players by Index:")
            for i, (_, player) in enumerate(top_players.iterrows(), 1):
                career_span = f"{player['year_min']:.0f}-{player['year_max']:.0f}"
                print(f"   {i:2d}. {player['player_name']:<25} Index: {player['index']:2.0f} (Career: {career_span})")
        
        print()
        
        # Index distribution
        if len(valid_indices) > 0:
            print("Index Distribution:")
            index_counts = valid_indices['index'].value_counts().sort_index(ascending=False)
            for index_val, count in index_counts.head(10).items():
                print(f"   - Index {index_val:2.0f}: {count:3d} players")
        
        print()
        
    else:
        print("[ERROR] Index results file not found.")
        print("Run the index calculation first:")
        print("python run_index_calculation.py")

def view_player_details(player_name):
    """View detailed index information for a specific player"""
    output_dir = "output"
    indices_file = os.path.join(output_dir, 'player_indices.csv')
    
    if not os.path.exists(indices_file):
        print("[ERROR] Index results file not found.")
        return
    
    data = pd.read_csv(indices_file)
    player_data = data[data['player_name'] == player_name]
    
    if len(player_data) == 0:
        print(f"[ERROR] Player '{player_name}' not found in index results")
        return
    
    player = player_data.iloc[0]
    
    print(f"Player: {player_name}")
    print("=" * 50)
    print(f"Index: {player['index']}")
    print(f"Career span: {player['year_min']:.0f}-{player['year_max']:.0f}")
    print(f"Seasons: {player['seasons']:.0f}")
    print(f"Age range: {player['age_min']:.0f}-{player['age_max']:.0f}")
    print(f"Points range: {player['points_min']:.0f}-{player['points_max']:.0f}")
    print(f"Average points: {player['points_avg']:.1f}")

def main():
    """Main function"""
    if len(sys.argv) > 1:
        player_name = sys.argv[1]
        view_player_details(player_name)
    else:
        view_index_results()

if __name__ == "__main__":
    main()
