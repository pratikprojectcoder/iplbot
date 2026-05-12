import os
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEAM_FEATURES_PATH = os.path.join(BASE_DIR, "..", "processed", "team_features.csv")
VENUE_FEATURES_PATH = os.path.join(BASE_DIR, "..", "processed", "venue_features.csv")
FINAL_FEATURES_PATH = os.path.join(BASE_DIR, "..", "processed", "final_match_features.csv")

feature_cols = [
    "team_last5_win_pct",
    "team_last5_runs_avg",
    "team_last5_powerplay_rpo",
    "team_last5_death_rpo",
    "team_overall_win_pct",
    "team_last5_run_rate",
    "team_batting_first_win_pct",
    "team_home_win_pct",
    "team_h2h_win_pct",
    "team_toss_win_pct",
    "team_toss_batting_first_win_pct",
    "team_toss_chase_win_pct",
    "team_toss_venue_win_pct",

    "opp_last5_win_pct",
    "opp_last5_runs_avg",
    "opp_last5_powerplay_rpo",
    "opp_last5_death_rpo",
    "opp_overall_win_pct",
    "opp_last5_run_rate",
    "opp_batting_first_win_pct",
    "opp_home_win_pct",
    "opp_h2h_win_pct",
    "opp_toss_win_pct",
    "opp_toss_batting_first_win_pct",
    "opp_toss_chase_win_pct",
    "opp_toss_venue_win_pct",

    "win_pct_diff",
    "runs_avg_diff",
    "powerplay_rpo_diff",
    "death_rpo_diff",
    "overall_win_pct_diff",
    "run_rate_diff",
    "batting_first_win_pct_diff",
    "home_win_pct_diff",
    "h2h_win_pct_diff",
    "toss_win_pct_diff",
    "toss_batting_first_win_pct_diff",
    "toss_chase_win_pct_diff",
    "toss_venue_win_pct_diff",

    "venue_avg_first_innings_score",
    "venue_chase_win_pct",
    "venue_avg_powerplay_runs",
    "venue_avg_middle_runs",
    "venue_avg_death_runs"
]


# =========================================
# Load training medians for NaN imputation
# =========================================

_feature_medians = {}

try:
    _train_df = pd.read_csv(FINAL_FEATURES_PATH)
    for col in feature_cols:
        if col in _train_df.columns:
            median_val = _train_df[col].median()
            _feature_medians[col] = 0.0 if np.isnan(median_val) else median_val
        else:
            _feature_medians[col] = 0.0
except Exception:
    _feature_medians = {col: 0.0 for col in feature_cols}


def _fill(value, col):
    """Return training median for col if value is None or NaN, else return value."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return _feature_medians.get(col, 0.0)
    try:
        if pd.isna(value):
            return _feature_medians.get(col, 0.0)
    except Exception:
        pass
    return value


# =========================================
# Lookup helpers
# =========================================

def get_latest_team_features(team_name, team_df):
    team_rows = team_df[team_df["team"] == team_name].copy()
    team_rows = team_rows.sort_values("date")
    if team_rows.empty:
        return None
    return team_rows.iloc[-1]


def get_latest_team_venue_features(team_name, venue_name, team_df):
    team_rows = team_df[
        (team_df["team"] == team_name) &
        (team_df["venue"] == venue_name)
    ].copy()
    team_rows = team_rows.sort_values("date")
    if team_rows.empty:
        return None
    return team_rows.iloc[-1]


def get_latest_venue_features(venue_name, venue_df):
    venue_rows = venue_df[venue_df["venue"] == venue_name].copy()
    venue_rows = venue_rows.sort_values("date")
    if venue_rows.empty:
        return None
    return venue_rows.iloc[-1]


def pick_value(primary_row, fallback_row, column_name):
    if primary_row is not None and column_name in primary_row.index:
        value = primary_row[column_name]
        if pd.notna(value):
            return value

    if fallback_row is not None and column_name in fallback_row.index:
        value = fallback_row[column_name]
        if pd.notna(value):
            return value

    return None


# =========================================
# Build match input row
# =========================================

def build_match_input(team, opponent, venue):
    team_df = pd.read_csv(TEAM_FEATURES_PATH)
    venue_df = pd.read_csv(VENUE_FEATURES_PATH)

    team_df["date"] = pd.to_datetime(team_df["date"], errors="coerce")
    venue_df["date"] = pd.to_datetime(venue_df["date"], errors="coerce")

    team_row = get_latest_team_features(team, team_df)
    opp_row = get_latest_team_features(opponent, team_df)
    venue_row = get_latest_venue_features(venue, venue_df)

    team_venue_row = get_latest_team_venue_features(team, venue, team_df)
    opp_venue_row = get_latest_team_venue_features(opponent, venue, team_df)

    if team_row is None:
        raise ValueError(f"No historical data found for team: {team}")
    if opp_row is None:
        raise ValueError(f"No historical data found for opponent: {opponent}")
    if venue_row is None:
        raise ValueError(f"No historical data found for venue: {venue}")

    team_toss_venue_win_pct = pick_value(team_venue_row, team_row, "team_toss_venue_win_pct")
    opp_toss_venue_win_pct = pick_value(opp_venue_row, opp_row, "team_toss_venue_win_pct")

    # Difference for toss_venue — compute only if both sides are available
    if pd.notna(team_toss_venue_win_pct) and pd.notna(opp_toss_venue_win_pct):
        toss_venue_diff = team_toss_venue_win_pct - opp_toss_venue_win_pct
    else:
        toss_venue_diff = None

    raw_row = {
        "team_last5_win_pct":               team_row["team_last5_win_pct"],
        "team_last5_runs_avg":              team_row["team_last5_runs_avg"],
        "team_last5_powerplay_rpo":         team_row["team_last5_powerplay_rpo"],
        "team_last5_death_rpo":             team_row["team_last5_death_rpo"],
        "team_overall_win_pct":             team_row["team_overall_win_pct"],
        "team_last5_run_rate":              team_row["team_last5_run_rate"],
        "team_batting_first_win_pct":       team_row["team_batting_first_win_pct"],
        "team_home_win_pct":                team_row["team_home_win_pct"],
        "team_h2h_win_pct":                 team_row["team_h2h_win_pct"],
        "team_toss_win_pct":                team_row["team_toss_win_pct"],
        "team_toss_batting_first_win_pct":  team_row["team_toss_batting_first_win_pct"],
        "team_toss_chase_win_pct":          team_row["team_toss_chase_win_pct"],
        "team_toss_venue_win_pct":          team_toss_venue_win_pct,

        "opp_last5_win_pct":                opp_row["team_last5_win_pct"],
        "opp_last5_runs_avg":               opp_row["team_last5_runs_avg"],
        "opp_last5_powerplay_rpo":          opp_row["team_last5_powerplay_rpo"],
        "opp_last5_death_rpo":              opp_row["team_last5_death_rpo"],
        "opp_overall_win_pct":              opp_row["team_overall_win_pct"],
        "opp_last5_run_rate":               opp_row["team_last5_run_rate"],
        "opp_batting_first_win_pct":        opp_row["team_batting_first_win_pct"],
        "opp_home_win_pct":                 opp_row["team_home_win_pct"],
        "opp_h2h_win_pct":                  opp_row["team_h2h_win_pct"],
        "opp_toss_win_pct":                 opp_row["team_toss_win_pct"],
        "opp_toss_batting_first_win_pct":   opp_row["team_toss_batting_first_win_pct"],
        "opp_toss_chase_win_pct":           opp_row["team_toss_chase_win_pct"],
        "opp_toss_venue_win_pct":           opp_toss_venue_win_pct,

        "win_pct_diff":                     team_row["team_last5_win_pct"] - opp_row["team_last5_win_pct"],
        "runs_avg_diff":                    team_row["team_last5_runs_avg"] - opp_row["team_last5_runs_avg"],
        "powerplay_rpo_diff":               team_row["team_last5_powerplay_rpo"] - opp_row["team_last5_powerplay_rpo"],
        "death_rpo_diff":                   team_row["team_last5_death_rpo"] - opp_row["team_last5_death_rpo"],
        "overall_win_pct_diff":             team_row["team_overall_win_pct"] - opp_row["team_overall_win_pct"],
        "run_rate_diff":                    team_row["team_last5_run_rate"] - opp_row["team_last5_run_rate"],
        "batting_first_win_pct_diff":       team_row["team_batting_first_win_pct"] - opp_row["team_batting_first_win_pct"],
        "home_win_pct_diff":                team_row["team_home_win_pct"] - opp_row["team_home_win_pct"],
        "h2h_win_pct_diff":                 team_row["team_h2h_win_pct"] - opp_row["team_h2h_win_pct"],
        "toss_win_pct_diff":                team_row["team_toss_win_pct"] - opp_row["team_toss_win_pct"],
        "toss_batting_first_win_pct_diff":  team_row["team_toss_batting_first_win_pct"] - opp_row["team_toss_batting_first_win_pct"],
        "toss_chase_win_pct_diff":          team_row["team_toss_chase_win_pct"] - opp_row["team_toss_chase_win_pct"],
        "toss_venue_win_pct_diff":          toss_venue_diff,

        "venue_avg_first_innings_score":    venue_row["venue_avg_first_innings_score"],
        "venue_chase_win_pct":              venue_row["venue_chase_win_pct"],
        "venue_avg_powerplay_runs":         venue_row["venue_avg_powerplay_runs"],
        "venue_avg_middle_runs":            venue_row["venue_avg_middle_runs"],
        "venue_avg_death_runs":             venue_row["venue_avg_death_runs"],
    }

    # Impute every NaN with training median
    clean_row = {col: _fill(raw_row[col], col) for col in feature_cols}

    return pd.DataFrame([clean_row])


if __name__ == "__main__":
    sample = build_match_input(
        team="Chennai Super Kings",
        opponent="Royal Challengers Bangalore",
        venue="MA Chidambaram Stadium"
    )
    print(sample[feature_cols])
