"""
NBA Player Performance Analysis Script
This script processes the large CSV files and calculates player performance indices
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import os

class NBAPlayerAnalyzer:
    def __init__(self, data_directory="."):
        self.data_directory = data_directory
        self.player_stats = None
        self.players = None
        self.games = None
        self.target_players = None
        
    def load_data(self):
        """Load all CSV files into memory"""
        print("Loading NBA data files...")
        
        # Load PlayerStatistics (the large file)
        print("Loading PlayerStatistics.csv (this may take a while)...")
        self.player_stats = pd.read_csv(os.path.join(self.data_directory, "PlayerStatistics.csv"))
        print(f"Loaded {len(self.player_stats):,} player statistics records")
        
        # Load other files
        self.players = pd.read_csv(os.path.join(self.data_directory, "Players.csv"))
        self.games = pd.read_csv(os.path.join(self.data_directory, "Games.csv"))
        self.target_players = pd.read_csv(os.path.join(self.data_directory, "target_player.csv"))
        
        print(f"Loaded {len(self.players):,} players")
        print(f"Loaded {len(self.games):,} games")
        print(f"Loaded {len(self.target_players):,} target players")
        
        # Convert gameDate to datetime
        self.player_stats['gameDate'] = pd.to_datetime(self.player_stats['gameDate'])
        self.games['gameDate'] = pd.to_datetime(self.games['gameDate'])
        
    def get_player_season_performance(self, player_id=None):
        """Calculate highest scoring game per season for each player"""
        print("Calculating player season performance...")
        
        # Filter for target players if specified
        if player_id:
            stats_data = self.player_stats[self.player_stats['personId'] == player_id].copy()
        else:
            # Use all players for now, but we'll filter to target players later
            stats_data = self.player_stats.copy()
        
        # Add season column
        stats_data['season'] = stats_data['gameDate'].dt.year
        
        # Filter out games where player didn't score (didn't play)
        stats_data = stats_data[stats_data['points'] > 0]
        
        # Group by player and season, find highest scoring game
        season_performance = stats_data.groupby(['personId', 'season']).agg({
            'points': ['max', 'mean', 'sum', 'count'],
            'assists': 'max',
            'reboundsTotal': 'max',
            'gameDate': 'min'  # First game of season
        }).reset_index()
        
        # Flatten column names
        season_performance.columns = [
            'personId', 'season', 'highestPoints', 'avgPoints', 
            'totalPoints', 'gamesPlayed', 'highestAssists', 
            'highestRebounds', 'firstGameDate'
        ]
        
        return season_performance
    
    def calculate_player_index(self, season_performance, weight_type='recent'):
        """Calculate player performance index based on highest scoring games per season"""
        print(f"Calculating player index with {weight_type} weighting...")
        
        current_year = datetime.now().year
        
        # Calculate season weights
        if weight_type == 'recent':
            # Recent seasons weighted higher
            season_performance['weight'] = season_performance['season'].apply(
                lambda x: 1.0 if x >= current_year - 5 
                else 0.8 if x >= current_year - 10 
                else 0.6 if x >= current_year - 20 
                else 0.4
            )
        elif weight_type == 'decade':
            # Weight by decade
            season_performance['weight'] = season_performance['season'].apply(
                lambda x: 1.0 if x >= 2020
                else 0.9 if x >= 2010
                else 0.8 if x >= 2000
                else 0.7 if x >= 1990
                else 0.6 if x >= 1980
                else 0.5 if x >= 1970
                else 0.4 if x >= 1960
                else 0.3
            )
        else:  # equal
            season_performance['weight'] = 1.0
        
        # Calculate weighted index
        season_performance['weightedPoints'] = season_performance['highestPoints'] * season_performance['weight']
        
        # Aggregate by player
        player_index = season_performance.groupby('personId').agg({
            'weightedPoints': 'sum',
            'highestPoints': ['max', 'mean'],
            'season': ['min', 'max', 'count'],
            'gamesPlayed': 'sum',
            'avgPoints': 'mean'
        }).reset_index()
        
        # Flatten column names
        player_index.columns = [
            'personId', 'playerIndex', 'careerHighPoints', 'avgSeasonHighPoints',
            'firstSeason', 'lastSeason', 'seasonsPlayed', 'totalGamesPlayed', 'avgPointsPerGame'
        ]
        
        # Merge with player names
        player_index = player_index.merge(
            self.players[['personId', 'firstName', 'lastName', 'birthdate', 'draftYear']], 
            on='personId', 
            how='left'
        )
        
        return player_index.sort_values('playerIndex', ascending=False)
    
    def get_target_players_analysis(self):
        """Analyze only the target players from the provided list"""
        print("Analyzing target players...")
        
        # Get target player IDs (assuming they match personId in Players table)
        # We need to match by name since target_player.csv might use different IDs
        target_names = set()
        for _, row in self.target_players.iterrows():
            name = f"{row['Player Name']}".lower().strip()
            target_names.add(name)
        
        # Find matching players
        self.players['fullName'] = (self.players['firstName'] + ' ' + self.players['lastName']).str.lower()
        target_player_ids = self.players[
            self.players['fullName'].isin(target_names)
        ]['personId'].tolist()
        
        print(f"Found {len(target_player_ids)} matching target players")
        
        # Get season performance for target players only
        target_stats = self.player_stats[
            self.player_stats['personId'].isin(target_player_ids)
        ].copy()
        
        target_stats['season'] = target_stats['gameDate'].dt.year
        target_stats = target_stats[target_stats['points'] > 0]
        
        return target_stats
    
    def export_results(self, player_index, filename_prefix="nba_analysis"):
        """Export results to JSON and CSV files"""
        print("Exporting results...")
        
        # Export top 100 players
        top_100 = player_index.head(100)
        
        # Export to JSON for web consumption
        json_data = top_100.to_dict('records')
        with open(f"{filename_prefix}_top100.json", 'w') as f:
            json.dump(json_data, f, indent=2, default=str)
        
        # Export to CSV
        top_100.to_csv(f"{filename_prefix}_top100.csv", index=False)
        
        # Export full results
        player_index.to_csv(f"{filename_prefix}_full_results.csv", index=False)
        
        print(f"Results exported to {filename_prefix}_*.json and {filename_prefix}_*.csv")
    
    def run_analysis(self):
        """Run the complete analysis"""
        print("Starting NBA Player Performance Analysis...")
        print("=" * 50)
        
        # Load data
        self.load_data()
        
        # Get season performance
        season_performance = self.get_player_season_performance()
        
        # Calculate player index with different weighting methods
        print("\nCalculating indices with different weighting methods:")
        
        # Recent weighting
        recent_index = self.calculate_player_index(season_performance, 'recent')
        print(f"Recent weighting: Top player is {recent_index.iloc[0]['firstName']} {recent_index.iloc[0]['lastName']} (Index: {recent_index.iloc[0]['playerIndex']:.2f})")
        
        # Equal weighting
        equal_index = self.calculate_player_index(season_performance, 'equal')
        print(f"Equal weighting: Top player is {equal_index.iloc[0]['firstName']} {equal_index.iloc[0]['lastName']} (Index: {equal_index.iloc[0]['playerIndex']:.2f})")
        
        # Export results
        self.export_results(recent_index, "nba_recent_weighted")
        self.export_results(equal_index, "nba_equal_weighted")
        
        return recent_index, equal_index

def main():
    """Main function to run the analysis"""
    analyzer = NBAPlayerAnalyzer()
    
    try:
        recent_results, equal_results = analyzer.run_analysis()
        
        print("\n" + "=" * 50)
        print("ANALYSIS COMPLETE!")
        print("=" * 50)
        print("Top 10 Players (Recent Weighting):")
        for i, (_, player) in enumerate(recent_results.head(10).iterrows(), 1):
            print(f"{i:2d}. {player['firstName']} {player['lastName']} - Index: {player['playerIndex']:.2f}")
        
        print("\nFiles created:")
        print("- nba_recent_weighted_top100.json")
        print("- nba_recent_weighted_top100.csv") 
        print("- nba_equal_weighted_top100.json")
        print("- nba_equal_weighted_top100.csv")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
