"""
Shared logic: per player-season, keep top 2 games by points plus all witness games
(points >= age_years at game time). Union and dedupe rows.
"""

from __future__ import annotations

import calendar
from datetime import date

import numpy as np
import pandas as pd


def _safe_calendar_date(year: int, month: int, day: int) -> date:
    """Clamp day to last day of month (handles Feb 29 on non-leap years)."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last_day))


def _parse_birth(val) -> date | None:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    s = str(val).strip()
    if s == "" or s.upper() == "NA" or s.lower() == "nat":
        return None
    for dayfirst in (True, False):
        ts = pd.to_datetime(s, dayfirst=dayfirst, errors="coerce")
        if pd.notna(ts):
            return ts.date()
    return None


def _coerce_game_date_series(series: pd.Series) -> pd.Series:
    """Parse gameDate; key logs use day/month/year (e.g. 30/12/1983 20:00)."""
    parsed = pd.to_datetime(series, errors="coerce", dayfirst=True)
    if parsed.isna().any():
        fallback = pd.to_datetime(series, errors="coerce", dayfirst=False)
        parsed = parsed.fillna(fallback)
    return parsed


def _parse_game_datetime(val) -> pd.Timestamp | None:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    if isinstance(val, pd.Timestamp):
        return val if pd.notna(val) else None
    ts = pd.to_datetime(val, errors="coerce", dayfirst=True)
    if pd.isna(ts):
        ts = pd.to_datetime(val, errors="coerce", dayfirst=False)
    if pd.isna(ts):
        return None
    return ts


def _age_years_days_at_game(birth_d: date, game_ts: pd.Timestamp) -> tuple[int, int]:
    g = game_ts.date()
    age_y = g.year - birth_d.year - ((g.month, g.day) < (birth_d.month, birth_d.day))
    last_bday = _safe_calendar_date(g.year, birth_d.month, birth_d.day)
    if last_bday > g:
        last_bday = _safe_calendar_date(g.year - 1, birth_d.month, birth_d.day)
    age_d = (g - last_bday).days
    return int(age_y), int(age_d)


def attach_game_date2(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "gameDate" not in out.columns:
        return out
    out["gameDate"] = _coerce_game_date_series(out["gameDate"])
    out["gameDate2"] = (
        out["gameDate"].dt.day.astype("Int64").astype(str)
        + "/"
        + out["gameDate"].dt.month.astype("Int64").astype(str)
        + "/"
        + out["gameDate"].dt.year.astype("Int64").astype(str)
    )
    return out


def normalize_key_game_logs(df: pd.DataFrame) -> pd.DataFrame:
    """
    Slim player*_key_game_logs.csv from ExtractKeyInfo: personId, birth_date, etc.
    """
    out = df.copy()
    if "person_id" not in out.columns and "personId" in out.columns:
        out["person_id"] = pd.to_numeric(out["personId"], errors="coerce")
    elif "person_id" in out.columns:
        out["person_id"] = pd.to_numeric(out["person_id"], errors="coerce")

    if "birthdate" not in out.columns and "birth_date" in out.columns:
        out["birthdate"] = out["birth_date"]
    elif "birthdate" not in out.columns:
        out["birthdate"] = pd.NA

    if "gameDate" not in out.columns and "gameDateTimeEst" in out.columns:
        out["gameDate"] = out["gameDateTimeEst"]

    if "gameDate" in out.columns:
        out["gameDate"] = _coerce_game_date_series(out["gameDate"])
    if "gameDate2" not in out.columns and "gameDate" in out.columns:
        out = attach_game_date2(out)

    out["points"] = pd.to_numeric(out["points"], errors="coerce")
    if "year" in out.columns:
        out["year"] = pd.to_numeric(out["year"], errors="coerce")
    return out


def prepare_key_logs_for_top_games_selection(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize slim key logs with Excel-filled age columns (age_years, age_days, age_at_game).
    Does not compute age in code.
    """
    out = normalize_key_game_logs(df)
    if "age_years" not in out.columns:
        raise ValueError(
            "age_years column required (add via Excel in player*_key_game_logs_age.csv)"
        )
    out["age_years"] = pd.to_numeric(out["age_years"], errors="coerce")
    if "age_days" in out.columns:
        out["age_days"] = pd.to_numeric(out["age_days"], errors="coerce")
    if "age_at_game" not in out.columns and "at_game" in out.columns:
        out["age_at_game"] = out["at_game"]
    return out


def attach_birthdate_from_players(df: pd.DataFrame, birthdate_map: dict) -> pd.DataFrame:
    out = df.copy()
    if "person_id" not in out.columns:
        raise ValueError("DataFrame must contain person_id")
    out["person_id"] = pd.to_numeric(out["person_id"], errors="coerce")
    out["birthdate"] = out["person_id"].map(birthdate_map)
    return out


def attach_age_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add age_years, age_days, age_at_game, birth_date from birthdate + gameDate."""
    out = df.copy()
    if "birthdate" not in out.columns:
        raise ValueError("birthdate column required before attach_age_columns")

    age_years: list[int | None] = []
    age_days: list[int | None] = []
    age_at_game: list[str | None] = []
    birth_dates: list[str | None] = []

    for _, row in out.iterrows():
        bd = _parse_birth(row["birthdate"])
        gd = _parse_game_datetime(row.get("gameDate"))
        if bd is None or gd is None:
            raw = row["birthdate"]
            birth_dates.append(str(raw).strip() if pd.notna(raw) else None)
            age_years.append(None)
            age_days.append(None)
            age_at_game.append(None)
            continue
        ay, ad = _age_years_days_at_game(bd, gd)
        birth_dates.append(f"{bd.day}/{bd.month}/{bd.year}")
        age_years.append(ay)
        age_days.append(ad)
        age_at_game.append(f"{ay}-{ad}")

    out["birth_date"] = birth_dates
    out["age_years"] = age_years
    out["age_days"] = age_days
    out["age_at_game"] = age_at_game
    return out


def _dedupe_key_columns(df: pd.DataFrame) -> list[str]:
    if "gameId" in df.columns and df["gameId"].notna().any():
        return ["person_id", "gameId"]
    return ["person_id", "year", "gameDate"]


def select_top2_plus_witness(df: pd.DataFrame, top_n: int = 2) -> pd.DataFrame:
    """
    top_n highest-point games per (person_id, year), plus every game with
    points >= age_years (witness). Requires age_years and points on df.
    """
    required = {"person_id", "year", "points", "gameDate", "age_years"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns for selection: {sorted(missing)}")

    work = df.copy()
    work["person_id"] = pd.to_numeric(work["person_id"], errors="coerce")
    work["points"] = pd.to_numeric(work["points"], errors="coerce")
    work["age_years"] = pd.to_numeric(work["age_years"], errors="coerce")
    work["gameDate"] = _coerce_game_date_series(work["gameDate"])

    sorted_df = work.sort_values(
        by=["person_id", "year", "points", "gameDate"],
        ascending=[True, True, False, False],
        kind="mergesort",
    )
    top = sorted_df.groupby(["person_id", "year"], sort=False).head(top_n)

    witness_mask = (
        work["points"].notna()
        & work["age_years"].notna()
        & (work["points"] >= work["age_years"])
    )
    witness = work.loc[witness_mask]

    merged = pd.concat([top, witness], ignore_index=True)
    keys = _dedupe_key_columns(merged)
    merged = merged.drop_duplicates(subset=keys, keep="first")
    return merged


def reorder_birthdate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Place gameDate2 and birthdate next to gameDate (same as legacy top2 scripts)."""
    columns = df.columns.tolist()
    if "gameDate" in columns and "gameDate2" in columns:
        columns.remove("gameDate2")
        game_date_idx = columns.index("gameDate") + 1
        columns.insert(game_date_idx, "gameDate2")
    if "gameDate" in columns and "birthdate" in columns:
        columns.remove("birthdate")
        game_date_idx = columns.index("gameDate") + 1
        if "gameDate2" in columns:
            game_date_idx += 1
        columns.insert(game_date_idx, "birthdate")
    return df[columns]
