#!/usr/bin/env python3
"""
Add personId to target_player.csv by matching Players.csv on
Clean Name + Birth Date(TextToColumn).

Handles duplicate names by using birthdate as the discriminator.
"""

from pathlib import Path
import re
import unicodedata

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
FALLBACK_DATA_DIR = BASE_DIR.parent / "data"
if not DATA_DIR.exists() and FALLBACK_DATA_DIR.exists():
    DATA_DIR = FALLBACK_DATA_DIR

PLAYERS_FILE = DATA_DIR / "Players.csv"
TARGET_FILE = DATA_DIR / "target_player.csv"
OUTPUT_FILE = DATA_DIR / "target_player_with_personId.csv"
MISSING_FILE = DATA_DIR / "target_player_missing_personId.csv"


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
    if not TARGET_FILE.exists():
        raise FileNotFoundError(f"Missing {TARGET_FILE}")

    players = pd.read_csv(PLAYERS_FILE)
    target = pd.read_csv(TARGET_FILE)

    if "Clean Name" not in target.columns or "Birth Date(TextToColumn)" not in target.columns:
        raise ValueError("target_player.csv must contain Clean Name and Birth Date(TextToColumn)")

    players["PlayerName"] = (players["firstName"].fillna("") + " " + players["lastName"].fillna("")).str.strip()
    players["PlayerName_norm"] = players["PlayerName"].map(normalize_name)
    players["lastName_norm"] = players["lastName"].map(normalize_name)
    players["birthdate_norm_mdy"] = pd.to_datetime(
        players["birthdate"], errors="coerce", dayfirst=False
    ).dt.date
    players["birthdate_norm_dmy"] = pd.to_datetime(
        players["birthdate"], errors="coerce", dayfirst=True
    ).dt.date
    players["has_birthdate"] = players["birthdate_norm_mdy"].notna() | players["birthdate_norm_dmy"].notna()

    target["clean_name_norm"] = target["Clean Name"].map(normalize_name)
    if "lastName" in target.columns:
        target["last_name_norm"] = target["lastName"].map(normalize_name)
    else:
        target["last_name_norm"] = ""
    target_birth_raw = target["Birth Date(TextToColumn)"]
    birth_mdy = pd.to_datetime(target_birth_raw, errors="coerce", dayfirst=False)
    birth_dmy = pd.to_datetime(target_birth_raw, errors="coerce", dayfirst=True)
    target["birthdate_norm_mdy"] = birth_mdy.dt.date
    target["birthdate_norm_dmy"] = birth_dmy.dt.date

    players_keyed = players.copy()

    def resolve_person_id(row) -> object:
        name_norm = row["clean_name_norm"]
        last_name_norm = row["last_name_norm"]
        birth_mdy = row["birthdate_norm_mdy"]
        birth_dmy = row["birthdate_norm_dmy"]
        if not name_norm:
            return None

        exact_name = players_keyed[players_keyed["PlayerName_norm"] == name_norm]
        if len(exact_name) == 1:
            return exact_name["personId"].iloc[0]
        if len(exact_name) > 1 and (pd.notna(birth_mdy) or pd.notna(birth_dmy)):
            exact_birth = exact_name[
                (exact_name["birthdate_norm_mdy"].isin([birth_mdy, birth_dmy]))
                | (exact_name["birthdate_norm_dmy"].isin([birth_mdy, birth_dmy]))
            ]
            if len(exact_birth) >= 1:
                return exact_birth["personId"].iloc[0]
            with_birthdate = exact_name[exact_name["has_birthdate"]]
            if len(with_birthdate) == 1:
                return with_birthdate["personId"].iloc[0]
        # Fallback: last name + birthdate matching
        if last_name_norm and (pd.notna(birth_mdy) or pd.notna(birth_dmy)):
            last_name_matches = players_keyed[players_keyed["lastName_norm"] == last_name_norm]
            if len(last_name_matches) > 0:
                last_birth = last_name_matches[
                    (last_name_matches["birthdate_norm_mdy"].isin([birth_mdy, birth_dmy]))
                    | (last_name_matches["birthdate_norm_dmy"].isin([birth_mdy, birth_dmy]))
                ]
                if len(last_birth) >= 1:
                    return last_birth["personId"].iloc[0]
        return None

    target["personId"] = target.apply(resolve_person_id, axis=1)

    target = target.drop(columns=["clean_name_norm", "last_name_norm", "birthdate_norm_mdy", "birthdate_norm_dmy"])
    target.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved: {OUTPUT_FILE}")

    missing = target[target["personId"].isna()].copy()
    if not missing.empty:
        missing.to_csv(MISSING_FILE, index=False)
        print(f"Saved missing personId list to: {MISSING_FILE}")


if __name__ == "__main__":
    main()
