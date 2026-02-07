#!/usr/bin/env python3
"""
Generate a diagnostic report for target_player2 rows missing personId.
Uses Birth Date(TextToColumn) as day/month/year (dayfirst=True).
"""

from pathlib import Path
import re
import unicodedata

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
PLAYERS_FILE = DATA_DIR / "Players.csv"
TARGET2_FILE = DATA_DIR / "target_player2.csv"
MISSING_FILE = DATA_DIR / "target_player2_missing_personId.csv"
OUTPUT_FILE = DATA_DIR / "target_player2_missing_diagnostics.csv"


def normalize_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    normalized = unicodedata.normalize("NFD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_name = ascii_name.replace("*", "").strip().lower()
    ascii_name = re.sub(r"[^\w\s]", " ", ascii_name)
    tokens = ascii_name.split()
    suffixes = {"jr", "sr", "ii", "iii", "iv", "v"}
    tokens = [t for t in tokens if t not in suffixes]
    return " ".join(tokens)


def main() -> None:
    if not PLAYERS_FILE.exists():
        raise FileNotFoundError(f"Missing {PLAYERS_FILE}")
    if not TARGET2_FILE.exists():
        raise FileNotFoundError(f"Missing {TARGET2_FILE}")

    players = pd.read_csv(PLAYERS_FILE)
    target2 = pd.read_csv(TARGET2_FILE)

    if "Clean Name" not in target2.columns or "Birth Date(TextToColumn)" not in target2.columns:
        raise ValueError("target_player2.csv must contain Clean Name and Birth Date(TextToColumn)")

    players["PlayerName"] = (players["firstName"].fillna("") + " " + players["lastName"].fillna("")).str.strip()
    players["PlayerName_norm"] = players["PlayerName"].map(normalize_name)
    players["birthdate_norm_mdy"] = pd.to_datetime(players["birthdate"], errors="coerce", dayfirst=False).dt.date
    players["birthdate_norm_dmy"] = pd.to_datetime(players["birthdate"], errors="coerce", dayfirst=True).dt.date
    players["has_birthdate"] = players["birthdate_norm_mdy"].notna() | players["birthdate_norm_dmy"].notna()

    target2["clean_name_norm"] = target2["Clean Name"].map(normalize_name)
    target2["birthdate_norm"] = pd.to_datetime(
        target2["Birth Date(TextToColumn)"], errors="coerce", dayfirst=True
    ).dt.date

    if MISSING_FILE.exists():
        missing = pd.read_csv(MISSING_FILE)
    else:
        missing = target2[target2.get("personId").isna()].copy()

    missing["clean_name_norm"] = missing["Clean Name"].map(normalize_name)
    missing["birthdate_norm"] = pd.to_datetime(
        missing["Birth Date(TextToColumn)"], errors="coerce", dayfirst=True
    ).dt.date

    diagnostics = []

    for _, row in missing.iterrows():
        name_norm = row["clean_name_norm"]
        birthdate = row["birthdate_norm"]
        candidates = players[players["PlayerName_norm"] == name_norm]

        if not candidates.empty:
            for _, cand in candidates.iterrows():
                diagnostics.append({
                    "Clean Name": row.get("Clean Name"),
                    "Birth Date(TextToColumn)": row.get("Birth Date(TextToColumn)"),
                    "Target Birthdate Parsed": birthdate,
                    "Candidate personId": cand.get("personId"),
                    "Candidate PlayerName": cand.get("PlayerName"),
                    "Candidate birthdate raw": cand.get("birthdate"),
                    "Candidate birthdate mdy": cand.get("birthdate_norm_mdy"),
                    "Candidate birthdate dmy": cand.get("birthdate_norm_dmy"),
                    "Candidate has birthdate": cand.get("has_birthdate"),
                })
        else:
            diagnostics.append({
                "Clean Name": row.get("Clean Name"),
                "Birth Date(TextToColumn)": row.get("Birth Date(TextToColumn)"),
                "Target Birthdate Parsed": birthdate,
                "Candidate personId": None,
                "Candidate PlayerName": None,
                "Candidate birthdate raw": None,
                "Candidate birthdate mdy": None,
                "Candidate birthdate dmy": None,
                "Candidate has birthdate": None,
            })

    diag_df = pd.DataFrame(diagnostics)
    diag_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved diagnostics to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
