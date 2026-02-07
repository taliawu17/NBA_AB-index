#!/usr/bin/env python3
"""
Generate a target player list from Players.csv and PlayerStatistics.csv
using criteria such as minimum seasons and minimum age at last game.
Also compare the generated list with the existing target_player.csv.
"""

import argparse
from pathlib import Path

import pandas as pd


def load_players(data_dir: Path) -> pd.DataFrame:
    players_path = data_dir / "Players.csv"
    if not players_path.exists():
        raise FileNotFoundError(f"Missing {players_path}")
    players = pd.read_csv(players_path)
    players["full_name"] = (players["firstName"].fillna("") + " " + players["lastName"].fillna("")).str.strip()
    players["birthdate"] = pd.to_datetime(players["birthdate"], errors="coerce")
    return players


def load_stats(data_dir: Path) -> pd.DataFrame:
    stats_path = data_dir / "PlayerStatistics.csv"
    if not stats_path.exists():
        raise FileNotFoundError(f"Missing {stats_path}")
    stats = pd.read_csv(stats_path, low_memory=False)
    stats["gameDate"] = pd.to_datetime(stats["gameDate"], errors="coerce")
    stats = stats.dropna(subset=["personId", "gameDate"])
    stats["season_year"] = stats["gameDate"].dt.year
    return stats


def compute_career_stats(stats: pd.DataFrame) -> pd.DataFrame:
    grouped = stats.groupby("personId")
    summary = grouped.agg(
        first_game=("gameDate", "min"),
        last_game=("gameDate", "max"),
        seasons_played=("season_year", "nunique"),
        games_played=("gameId", "nunique"),
    ).reset_index()
    summary["career_length_years"] = summary["last_game"].dt.year - summary["first_game"].dt.year + 1
    return summary


def add_age_at_last_game(players: pd.DataFrame, career: pd.DataFrame) -> pd.DataFrame:
    merged = career.merge(players[["personId", "full_name", "birthdate"]], on="personId", how="left")
    merged["age_at_last_game"] = (merged["last_game"] - merged["birthdate"]).dt.days / 365.25
    return merged


def filter_targets(merged: pd.DataFrame, min_seasons: int, min_age: float) -> pd.DataFrame:
    filtered = merged[
        (merged["seasons_played"] >= min_seasons)
        & (merged["age_at_last_game"].notna())
        & (merged["age_at_last_game"] >= min_age)
    ].copy()
    return filtered


def compare_with_existing(generated: pd.DataFrame, data_dir: Path) -> pd.DataFrame:
    target_path = data_dir / "target_player.csv"
    if not target_path.exists():
        return pd.DataFrame()
    target = pd.read_csv(target_path)
    target["full_name"] = target["Player Name"].astype(str).str.strip().str.lower()
    generated["full_name_norm"] = generated["full_name"].str.lower()

    generated["in_existing_target"] = generated["full_name_norm"].isin(set(target["full_name"]))
    return generated.sort_values(["in_existing_target", "full_name"], ascending=[False, True])


def main() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Generate target players from criteria.")
    parser.add_argument("--data-dir", default=str(base_dir / "data"), help="Directory with CSV data")
    parser.add_argument("--output-dir", default=str(base_dir / "output"), help="Output directory")
    parser.add_argument("--min-seasons", type=int, default=3, help="Minimum seasons played")
    parser.add_argument("--min-age", type=float, default=33.0, help="Minimum age at last game")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    players = load_players(data_dir)
    stats = load_stats(data_dir)
    career = compute_career_stats(stats)
    merged = add_age_at_last_game(players, career)
    filtered = filter_targets(merged, args.min_seasons, args.min_age)

    generated_path = output_dir / "generated_target_players.csv"
    filtered.sort_values("full_name").to_csv(generated_path, index=False)

    comparison = compare_with_existing(filtered, data_dir)
    if not comparison.empty:
        comparison_path = output_dir / "generated_vs_existing_target.csv"
        comparison.to_csv(comparison_path, index=False)

    print(f"Generated target list: {generated_path}")
    if not comparison.empty:
        print(f"Comparison file: {comparison_path}")
    print(f"Total generated: {len(filtered)}")


if __name__ == "__main__":
    main()
