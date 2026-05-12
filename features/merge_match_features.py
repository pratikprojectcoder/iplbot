import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEAM_FEATURES_PATH = os.path.join(BASE_DIR, "..", "processed", "team_features.csv")
VENUE_FEATURES_PATH = os.path.join(BASE_DIR, "..", "processed", "venue_features.csv")
OUTPUT_PATH = os.path.join(BASE_DIR, "..", "processed", "final_match_features.csv")

team_df = pd.read_csv(TEAM_FEATURES_PATH)
venue_df = pd.read_csv(VENUE_FEATURES_PATH)

team_df["date"] = pd.to_datetime(team_df["date"], errors="coerce")
venue_df["date"] = pd.to_datetime(venue_df["date"], errors="coerce")

merge_cols = ["match_id", "date", "team", "opponent", "venue"]

final_df = team_df.merge(
    venue_df,
    on=merge_cols,
    how="left"
)

selected_columns = [
    "match_id",
    "date",
    "team",
    "opponent",
    "venue",
    "result_win",

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

final_df = final_df[selected_columns].copy()
final_df = final_df.sort_values(["date", "match_id", "team"]).reset_index(drop=True)

os.makedirs(os.path.join(BASE_DIR, "..", "processed"), exist_ok=True)
final_df.to_csv(OUTPUT_PATH, index=False)

print("final_match_features.csv created successfully")
print("Total rows:", len(final_df))
print(final_df.head())
print("\nColumns:")
print(final_df.columns.tolist())