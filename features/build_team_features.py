import pandas as pd
import os
import numpy as np

HOME_VENUES = {
    "Chennai Super Kings": "MA Chidambaram Stadium",
    "Mumbai Indians": "Wankhede Stadium",
    "Kolkata Knight Riders": "Eden Gardens",
    "Royal Challengers Bangalore": "M Chinnaswamy Stadium",
    "Delhi Capitals": "Arun Jaitley Stadium",
    "Punjab Kings": "Punjab Cricket Association Stadium",
    "Rajasthan Royals": "Sawai Mansingh Stadium",
    "Sunrisers Hyderabad": "Rajiv Gandhi International Stadium",
    "Lucknow Super Giants": "BRSABV Ekana Stadium",
    "Gujarat Titans": "Narendra Modi Stadium"
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_PATH = os.path.join(BASE_DIR, "..", "processed", "team_match_stats.csv")
OUTPUT_PATH = os.path.join(BASE_DIR, "..", "processed", "team_features.csv")


df = pd.read_csv(INPUT_PATH)

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.sort_values(["team", "date", "match_id"]).reset_index(drop=True)

# -----------------------------
# Base phase metrics
# -----------------------------
df["powerplay_rpo"] = df["powerplay_runs"] / 6
df["middle_rpo"] = df["middle_runs"] / 9
df["death_rpo"] = df["death_runs"] / 5

# -----------------------------
# Home venue flag
# -----------------------------
df["is_home"] = df.apply(
    lambda x: 1 if HOME_VENUES.get(x["team"], "") in str(x["venue"]) else 0,
    axis=1
)

# -----------------------------
# Existing core features
# -----------------------------
df["team_last5_win_pct"] = (
    df.groupby("team")["result_win"]
    .transform(lambda x: x.shift(1).rolling(5).mean())
)

df["team_last5_runs_avg"] = (
    df.groupby("team")["runs_scored"]
    .transform(lambda x: x.shift(1).rolling(5).mean())
)

df["team_last5_powerplay_rpo"] = (
    df.groupby("team")["powerplay_rpo"]
    .transform(lambda x: x.shift(1).rolling(5).mean())
)

df["team_last5_death_rpo"] = (
    df.groupby("team")["death_rpo"]
    .transform(lambda x: x.shift(1).rolling(5).mean())
)

df["team_overall_win_pct"] = (
    df.groupby("team")["result_win"]
    .transform(lambda x: x.shift(1).expanding().mean())
)

df["team_last5_run_rate"] = (
    df.groupby("team")["run_rate"]
    .transform(lambda x: x.shift(1).rolling(5).mean())
)

# -----------------------------
# Batting first win %
# -----------------------------
df["batting_first_result"] = np.where(
    df["batted_first"] == 1,
    df["result_win"],
    np.nan
)

df["team_batting_first_win_pct"] = (
    df.groupby("team")["batting_first_result"]
    .transform(lambda x: x.shift(1).expanding().mean())
)

# -----------------------------
# Home ground win %
# -----------------------------
df["home_result"] = np.where(
    df["is_home"] == 1,
    df["result_win"],
    np.nan
)

df["team_home_win_pct"] = (
    df.groupby("team")["home_result"]
    .transform(lambda x: x.shift(1).expanding().mean())
)

# -----------------------------
# H2H win %
# -----------------------------
df["pair_key"] = df.apply(
    lambda x: " vs ".join(sorted([str(x["team"]), str(x["opponent"])])),
    axis=1
)

df["team_h2h_win_pct"] = (
    df.groupby(["pair_key", "team"])["result_win"]
    .transform(lambda x: x.shift(1).expanding().mean())
)

# =====================================================
# NEW TOSS FEATURES
# =====================================================

# Toss win %
df["toss_result"] = np.where(
    df["toss_won"] == 1,
    df["result_win"],
    np.nan
)

df["team_toss_win_pct"] = (
    df.groupby("team")["toss_result"]
    .transform(lambda x: x.shift(1).expanding().mean())
)

# Toss + batting first win %
df["toss_batting_first_result"] = np.where(
    (df["toss_won"] == 1) & (df["batted_first"] == 1),
    df["result_win"],
    np.nan
)

df["team_toss_batting_first_win_pct"] = (
    df.groupby("team")["toss_batting_first_result"]
    .transform(lambda x: x.shift(1).expanding().mean())
)

# Toss + chase win %
df["toss_chase_result"] = np.where(
    (df["toss_won"] == 1) & (df["batted_first"] == 0),
    df["result_win"],
    np.nan
)

df["team_toss_chase_win_pct"] = (
    df.groupby("team")["toss_chase_result"]
    .transform(lambda x: x.shift(1).expanding().mean())
)

# Toss + venue win %
df["toss_venue_result"] = np.where(
    df["toss_won"] == 1,
    df["result_win"],
    np.nan
)

df["team_toss_venue_win_pct"] = (
    df.groupby(["team", "venue"])["toss_venue_result"]
    .transform(lambda x: x.shift(1).expanding().mean())
)

# -----------------------------
# Opponent feature table
# -----------------------------
opp_features = df[[
    "match_id",
    "team",
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
    "team_toss_venue_win_pct"
]].copy()

opp_features = opp_features.rename(columns={
    "team": "opponent",
    "team_last5_win_pct": "opp_last5_win_pct",
    "team_last5_runs_avg": "opp_last5_runs_avg",
    "team_last5_powerplay_rpo": "opp_last5_powerplay_rpo",
    "team_last5_death_rpo": "opp_last5_death_rpo",
    "team_overall_win_pct": "opp_overall_win_pct",
    "team_last5_run_rate": "opp_last5_run_rate",
    "team_batting_first_win_pct": "opp_batting_first_win_pct",
    "team_home_win_pct": "opp_home_win_pct",
    "team_h2h_win_pct": "opp_h2h_win_pct",
    "team_toss_win_pct": "opp_toss_win_pct",
    "team_toss_batting_first_win_pct": "opp_toss_batting_first_win_pct",
    "team_toss_chase_win_pct": "opp_toss_chase_win_pct",
    "team_toss_venue_win_pct": "opp_toss_venue_win_pct"
})

df = df.merge(
    opp_features,
    on=["match_id", "opponent"],
    how="left"
)

# -----------------------------
# Difference features
# -----------------------------
df["win_pct_diff"] = df["team_last5_win_pct"] - df["opp_last5_win_pct"]
df["runs_avg_diff"] = df["team_last5_runs_avg"] - df["opp_last5_runs_avg"]
df["powerplay_rpo_diff"] = df["team_last5_powerplay_rpo"] - df["opp_last5_powerplay_rpo"]
df["death_rpo_diff"] = df["team_last5_death_rpo"] - df["opp_last5_death_rpo"]
df["overall_win_pct_diff"] = df["team_overall_win_pct"] - df["opp_overall_win_pct"]
df["run_rate_diff"] = df["team_last5_run_rate"] - df["opp_last5_run_rate"]
df["batting_first_win_pct_diff"] = df["team_batting_first_win_pct"] - df["opp_batting_first_win_pct"]
df["home_win_pct_diff"] = df["team_home_win_pct"] - df["opp_home_win_pct"]
df["h2h_win_pct_diff"] = df["team_h2h_win_pct"] - df["opp_h2h_win_pct"]

df["toss_win_pct_diff"] = df["team_toss_win_pct"] - df["opp_toss_win_pct"]
df["toss_batting_first_win_pct_diff"] = (
    df["team_toss_batting_first_win_pct"] - df["opp_toss_batting_first_win_pct"]
)
df["toss_chase_win_pct_diff"] = (
    df["team_toss_chase_win_pct"] - df["opp_toss_chase_win_pct"]
)
df["toss_venue_win_pct_diff"] = (
    df["team_toss_venue_win_pct"] - df["opp_toss_venue_win_pct"]
)

# -----------------------------
# Cleanup
# -----------------------------
df = df.drop(columns=[
    "batting_first_result",
    "home_result",
    "pair_key",
    "toss_result",
    "toss_batting_first_result",
    "toss_chase_result",
    "toss_venue_result"
])

os.makedirs(os.path.join(BASE_DIR, "..", "processed"), exist_ok=True)
df.to_csv(OUTPUT_PATH, index=False)

print("team_features.csv created successfully")
print("Shape:", df.shape)
print(df.head())
print("\nColumns:")
print(df.columns.tolist())