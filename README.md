# NBA AB-Index Pipeline

This repo computes AB-index rankings for NBA players using historical game logs.

## Data (place in `data/`)

Required inputs:
- `Players.csv` (from Kaggle)
- `PlayerStatistics.csv` (from Kaggle)
- `target_player.csv` (batch 1, 1635 players)
- `target_player2.csv` (batch 2, 1049 players)
- `player_id_v3.csv` (curated list, if you rebuild target lists)

## Pipeline overview

1) Start with `Players.csv`, `PlayerStatistics.csv`, `target_player.csv`, and `target_player2.csv`.
2) Add `personId` to both target lists using `Players.csv`.
   - Some players cannot be matched automatically due to name differences.
   - Unmatched players were manually verified and corrected.
3) Extract all game logs for target players from `PlayerStatistics.csv`.
4) Create key log tables and compute `age_years` (manual step), then calculate AB-index.
5) Rank indices with the batch-specific ranking scripts.
6) Combine and rank both batches together.

## Batch 1 (target_player.csv)

### 1. Add personId
```
python db_scripts/add_personid_target_player.py
```
Output:
- `data/target_player_with_personId.csv`
- `data/target_player_missing_personId.csv`

### 2. Extract game logs
```
python db_scripts/extract_game_logs.py
```
Output:
- `output/all_player_game_logs.csv`
- `output/all_player_game_logs_regular_season.csv`
- `output/duplicate_players.txt`
- `output/missing_personid_players.csv`

### 3. Extract key fields (for manual age_years calculation)
```
python db_scripts/ExtractKeyInfo.py
```
Output:
- `output/player1_key_game_logs.csv`

### 4. Calculate AB-index (player1 key logs)
```
python db_scripts/calculate_indices_player1.py
```
Input:
- `output/player1_key_game_logs - Copy.csv`
Output:
- `output/player1_index.csv`

### 5. Rank player1 indices
```
python db_scripts/rank_indices_player1.py
```
Output:
- `output/player1_index_ranked.csv`

## Batch 2 (target_player2.csv)

### 1. Add personId
```
python db_scripts/add_personid_target_player2.py
```
Output:
- `data/target_player2_with_personId.csv`
- `data/target_player2_missing_personId.csv`

### 2. Extract game logs
```
python db_scripts/extract_game_logs_target2.py
```
Output:
- `output/all_player2_game_logs.csv` (all game types)
- `output/all_player_game_logs_regular_season.csv` (regular season only)
- `output/duplicate_players_target2.txt`
- `output/missing_personid_players_target2.csv`

### 3. Extract key fields (for manual age_years calculation)
```
python db_scripts/ExtractKeyInfo_player2.py
```
Output:
- `output/player2_key_game_logs.csv`

### 4. Calculate AB-index (player2 key logs)
```
python db_scripts/calculate_indices_player2.py
```
Output:
- `output/player2_index.csv`
- `output/duplicate_clean_name_player2.csv` (only if duplicates exist)

### 5. Rank player2 indices
```
python db_scripts/rank_indices_player2.py
```
Output:
- `output/player2_index_ranked.csv`

## Combine both batches

```
python db_scripts/combine_player_indices.py
```
Output:
- `output/player_indices_combined.csv`
- `output/player_indices_combined_ranked.csv`

## Notes

- All scripts use relative paths based on the repo root.
- Keep intermediate CSVs in `output/` for downstream steps.
