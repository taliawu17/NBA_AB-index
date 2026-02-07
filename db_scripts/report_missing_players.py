#!/usr/bin/env python3
"""
Report target players filtered out due to missing/invalid personId
or missing regular-season game logs.
"""

from pathlib import Path

import pandas as pd


def main() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / "data"
    output_dir = base_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        target = pd.read_csv(data_dir / "target_player.csv")
    except UnicodeDecodeError:
        target = pd.read_csv(data_dir / "target_player.csv", encoding="latin1")
    stats = pd.read_csv(data_dir / "PlayerStatistics.csv", usecols=["personId"])
    regular_logs = pd.read_csv(output_dir / "all_player_game_logs_regular_season.csv", usecols=["person_id"])

    stats_ids = set(stats["personId"].dropna().astype(int))
    regular_ids = set(regular_logs["person_id"].dropna().astype(int))

    target["personId"] = pd.to_numeric(target.get("personId"), errors="coerce")

    reasons = []
    for _, row in target.iterrows():
        pid = row["personId"]
        if pd.isna(pid):
            reason = "missing personId"
        else:
            pid_int = int(pid)
            if pid_int not in stats_ids:
                reason = "invalid personId"
            elif pid_int not in regular_ids:
                reason = "missing regular-season game logs"
            else:
                continue

        reasons.append({
            "Player Name": row.get("Player Name"),
            "Clean Name": row.get("Clean Name"),
            "Birth Date": row.get("Birth Date"),
            "personId": pid,
            "Reason": reason,
        })

    report_df = pd.DataFrame(reasons)
    report_path = output_dir / "filtered_out_players.csv"
    report_df.to_csv(report_path, index=False)

    print(f"Saved report to: {report_path}")
    print(f"Total filtered out: {len(report_df)}")


if __name__ == "__main__":
    main()
