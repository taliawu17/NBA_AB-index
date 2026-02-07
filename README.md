<<<<<<< HEAD
# NBA_AB-index
NBA AB‑Index pipeline and rankings
=======
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
4) For each season, keep **two** games with the highest points.
   - Ties are resolved by **latest game date**.
5) Calculate AB-index using `calculate_indices.py` / `calculate_indices_player2.py`.

## Batch 1 (target_player.csv)

### 1. Add personId
```
python db_scripts/add_personid_target_player2.py
```
Output:
- `data/target_player2_with_personId.csv`
- `data/target_player2_missing_personId.csv`

### 2. Extract game logs
```
python db_scripts/extract_game_logs.py
```
Output:
- `output/all_player_game_logs.csv`
- `output/all_player_game_logs_regular_season.csv`

### 3. Select top 2 games per season
```
python db_scripts/select_top2_games_per_season.py
```
Output:
- `output/top2_games_per_season.csv`

### 4. Fill birthdates
```
python db_scripts/fill_birthdate_top2.py
```
Output:
- `output/top2_games_per_season_with_birthdate.csv`

### 5. Calculate AB-index
```
python db_scripts/calculate_indices.py
```
Output:
- `output/player_indices_20260204.csv`
- `output/player_indices_ranked_20260204.csv`

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
- `output/all_player2_game_logs.csv`

### 3. Select top 2 games per season
```
python db_scripts/select_top2_games_per_season_target2.py
```
Output:
- `output/top2_games_per_season_player2.csv`

### 4. Fill birthdates
```
python db_scripts/fill_birthdate_top2_player2.py
```
Output:
- `output/top2_games_per_season_with_birthdate_player2.csv`

### 5. Calculate AB-index
```
python db_scripts/calculate_indices_player2.py
```
Output:
- `output/player_indices_player2_20260204.csv`
- `output/player_indices_ranked_player2_20260204.csv`

## Notes

- All scripts use relative paths based on the repo root.
- Keep intermediate CSVs in `output/` for downstream steps.
>>>>>>> 385cfd7 (Initial commit)
