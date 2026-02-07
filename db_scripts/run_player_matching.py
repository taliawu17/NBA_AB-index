#!/usr/bin/env python3
"""
Run only the player matching step and save:
- updated target_player.csv with personId
- output/missing_target_players.csv
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nba_player_analysis import NBAPlayerGameLogExtractor  # noqa: E402


def main() -> None:
    extractor = NBAPlayerGameLogExtractor()
    extractor.load_data()
    extractor.handle_player_uniqueness()


if __name__ == "__main__":
    main()
