# NBA AB-Index Pipeline

This repo computes AB-index rankings for NBA players using historical game logs (three cohorts, then one combined ranking).

## Data (place in `data/`)

- `Players.csv`, `PlayerStatistics.csv` (Kaggle; batch 3 may use `data/up2_2526/PlayerStatistics.csv`)
- `target_player.csv` (batch 1)
- `target_player2.csv` (batch 2)
- `target_player3_with_personId.csv` (batch 3)
- `player_id_v3.csv` (optional, for `build_3rankings.py` / player_id column)

## Pipeline overview

1. Add `personId` to each target list (`Players.csv`).
2. Extract regular-season game logs from `PlayerStatistics.csv`.
3. **`ExtractKeyInfo_playerN.py`** → slim key logs → add `age_at_game`, `age_years`, `age_days` in **Excel** → `playerN_key_game_logs_age.csv`.
4. Select **top-2 games per season + witness games** → `top_games_per_season_playerN.csv`.
5. Calculate AB-index → `playerN_index.csv` (includes `personId`).
6. Rank valid indices (`index >= 18`) → `playerN_index_ranked.csv`.
7. **Combine** all batches, dedupe by `personId`, rank → `player_index_all.csv` / `player_index_ranked_all.csv`.

Batch 3 overlaps **batch 1** (same `personId`s); step 7 keeps one row per player (highest `index`, then `age_years`, then `age_days`).

Index rule: \(k = \max \min(\text{age\_years}, \text{points})\) over top games; \(k < 18\) → `NA`. Code: `db_scripts/calculate_indices.py`.

---

## Scripts (steps 1–3 by batch)

| Step | Batch 1 | Batch 2 | Batch 3 |
|------|---------|---------|---------|
| personId | `db_scripts/add_personid_target_player1.py` | `db_scripts/add_personid_target_player2.py` | (in `target_player3_with_personId.csv`) |
| extract logs | `db_scripts/extract_game_logs_player1.py` | `db_scripts/extract_game_logs_player2.py` | `db_scripts/build_target_player3.py` (if needed) |
| | | | `db_scripts/extract_game_logs_target3.py` |
| key logs | `db_scripts/ExtractKeyInfo_player1.py` | `db_scripts/ExtractKeyInfo_player2.py` | build `player3_key_game_logs.csv` manually or from logs; then Excel ages |

**Extract outputs (`output/`):**

| Batch | Main log files |
|-------|----------------|
| 1 | `all_player_game_logs.csv`, `all_player_game_logs_regular_season.csv` |
| 2 | `all_player2_game_logs.csv`, `player2_game_logs_regular_season.csv` |
| 3 | `all_player3_game_logs.csv`, `all_player3_game_logs_regular_season.csv` |

**Key logs:** `playerN_key_game_logs.csv` → Excel → `playerN_key_game_logs_age.csv`

---

## Steps 4–7 (same pattern; change `N` = 1, 2, 3)

**Step 4 — `db_scripts/select_top_games_per_season_playerN.py`** (`top_games_selection.py`):  
Per player-season: **top 2** games by `points` (tie-break: later `gameDate`) ∪ **witness** games (`points >= age_years`), then dedupe.

**Step 5 — `db_scripts/calculate_indices_playerN.py`:**  
Input: `top_games_per_season_playerN.csv` → output `playerN_index.csv`.  
Override: env `CALCULATE_INDICES_PLAYER1_INPUT` / `..._PLAYER2_...` / `..._PLAYER3_...`.

**Step 6 — rank:**  
- Batch 1 & 3: `db_scripts/rank_indices_player1.py`, `db_scripts/rank_indices_player3.py`  
- Batch 2: `calculate_indices_player2.py` also writes `player2_index_ranked.csv`; optional re-run with `db_scripts/rank_indices_player2.py`

```bash
python db_scripts/select_top_games_per_season_player1.py
python db_scripts/calculate_indices_player1.py
python db_scripts/rank_indices_player1.py

python db_scripts/select_top_games_per_season_player2.py
python db_scripts/calculate_indices_player2.py
python db_scripts/rank_indices_player2.py

python db_scripts/select_top_games_per_season_player3.py
python db_scripts/calculate_indices_player3.py
python db_scripts/rank_indices_player3.py
```

**Step 7 — combine** (reads `player1_index.csv`, `player2_index.csv`, `player3_index.csv`, not the per-batch ranked files):

```bash
python db_scripts/combine_player_indices.py
```

Optional follow-ups (local only; not in the GitHub repo):

```bash
python db_scripts/add_before_after_2014.py      # adds BeforeAfter2014 to player_index_ranked_all.csv
python db_scripts/build_3rankings.py            # -> 3rankings_20260518.csv (NBA75 ∪ B100 ∪ AB≥33)
python db_scripts/qa_top_games.py
```

---

## Main outputs

### `output/`

| File | |
|------|--|
| `playerN_key_game_logs.csv` | Slim logs from ExtractKeyInfo |
| `playerN_key_game_logs_age.csv` | + Excel ages |
| `top_games_per_season_playerN.csv` | Top-2 + witness |
| `playerN_index.csv` | AB-index per player (`personId`, witness stats) |
| `playerN_index_ranked.csv` | Valid index only, sorted |
| `player_index_all.csv` | Combined, deduped (all players, incl. `NA`) |
| `player_index_ranked_all.csv` | Combined valid indices + `AB_rank` 1…N |

### Repo root (analysis / figures)

| File | |
|------|--|
| `3rankings_20260518.csv` | Union table for Venn / cross-rankings (`V_index`, `V_ranking` = AB index / `AB_rank`) |
| `nba75_latestGame.csv` | NBA75 list + last-game ages + AB-index |
| `figure3_3way.png` | From `figure3.new.hatch.py` + `3rankings_20260518.csv` |

Legacy copies of older scripts live under `db_scripts/store/`.

---

## Notes

- Run commands from the **repo root**.
- Batch 1 `gameDate` in key logs is often `d/m/y`; `top_games_selection.py` uses `dayfirst=True` when parsing.
- Remove non-player rows from key logs (e.g. coaching appearances) before step 4.
- `clean_name` in top games is mapped to `player_name` in index scripts.
- See `requirements.txt` (Python 3.10+).

## Preprint
The AgeBreaker Index: Age-Defying Single-Game Scoring Among Veteran NBA Players
DOI: https://doi.org/10.51224/SportRxiv.926
