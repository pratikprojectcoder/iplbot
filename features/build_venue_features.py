import pandas as pd
import os

MATCHES_INPUT = "processed/matches_clean.csv"
TEAM_INPUT = "processed/team_match_stats.csv"
OUTPUT_PATH = "processed/venue_features.csv"

# -------------------------------
# Load datasets
# -------------------------------
matches_df = pd.read_csv(MATCHES_INPUT)
team_df = pd.read_csv(TEAM_INPUT)

matches_df["date"] = pd.to_datetime(matches_df["date"], errors="coerce")
team_df["date"] = pd.to_datetime(team_df["date"], errors="coerce")

matches_df = matches_df.sort_values("date").reset_index(drop=True)
team_df = team_df.sort_values("date").reset_index(drop=True)

# -------------------------------
# Build match-level helpers from team table
# -------------------------------

# First innings score
innings1_df = team_df[team_df["innings"] == 1][["match_id", "runs_scored"]].copy()
innings1_df = innings1_df.rename(columns={"runs_scored": "first_innings_score"})

# Chasing team won? (innings 2 row result)
innings2_df = team_df[team_df["innings"] == 2][["match_id", "result_win"]].copy()
innings2_df = innings2_df.rename(columns={"result_win": "chasing_team_won"})

# Merge helpers into matches_df
matches_df = matches_df.merge(innings1_df, on="match_id", how="left")
matches_df = matches_df.merge(innings2_df, on="match_id", how="left")

# -------------------------------
# Match-level venue features
# -------------------------------

matches_df["venue_avg_first_innings_score"] = (
    matches_df.groupby("venue")["first_innings_score"]
    .transform(lambda x: x.shift(1).expanding().mean())
)

matches_df["venue_chase_win_pct"] = (
    matches_df.groupby("venue")["chasing_team_won"]
    .transform(lambda x: x.shift(1).expanding().mean())
)

venue_match_features = matches_df[[
    "match_id",
    "venue_avg_first_innings_score",
    "venue_chase_win_pct"
]].copy()

# -------------------------------
# Team-level venue phase features
# -------------------------------

team_df["venue_avg_powerplay_runs"] = (
    team_df.groupby("venue")["powerplay_runs"]
    .transform(lambda x: x.shift(1).expanding().mean())
)

team_df["venue_avg_middle_runs"] = (
    team_df.groupby("venue")["middle_runs"]
    .transform(lambda x: x.shift(1).expanding().mean())
)

team_df["venue_avg_death_runs"] = (
    team_df.groupby("venue")["death_runs"]
    .transform(lambda x: x.shift(1).expanding().mean())
)

team_df = team_df.merge(venue_match_features, on="match_id", how="left")

venue_features_df = team_df[[
    "match_id",
    "date",
    "team",
    "opponent",
    "venue",
    "venue_avg_first_innings_score",
    "venue_chase_win_pct",
    "venue_avg_powerplay_runs",
    "venue_avg_middle_runs",
    "venue_avg_death_runs"
]].copy()

os.makedirs("processed", exist_ok=True)
venue_features_df.to_csv(OUTPUT_PATH, index=False)

print("venue_features.csv created successfully")
print("Total rows:", len(venue_features_df))
print(venue_features_df.head())