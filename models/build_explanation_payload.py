import os
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "processed", "final_match_features.csv")

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


def load_and_prepare_data():
    df = pd.read_csv(DATA_PATH)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna().drop_duplicates().reset_index(drop=True)

    split_date = "2019-01-01"

    train_df = df[df["date"] < split_date].copy()
    test_df = df[df["date"] >= split_date].copy()

    X_train = train_df[feature_cols]
    y_train = train_df["result_win"]

    X_test = test_df[feature_cols]
    y_test = test_df["result_win"]

    meta_test = test_df[["match_id", "date", "team", "opponent", "venue"]].reset_index(drop=True)

    return X_train, y_train, X_test, y_test, meta_test


def train_random_forest(X_train, y_train):
    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=42
    )
    rf.fit(X_train, y_train)
    return rf


def build_explanation_payload(sample_index=0):
    X_train, y_train, X_test, y_test, meta_test = load_and_prepare_data()
    rf = train_random_forest(X_train, y_train)

    sample_row = X_test.iloc[sample_index]
    sample_meta = meta_test.iloc[sample_index]
    sample_prob = float(rf.predict_proba(X_test.iloc[[sample_index]])[:, 1][0])

    feature_df = pd.DataFrame({
        "feature": feature_cols,
        "value": sample_row.values,
        "importance": rf.feature_importances_
    })

    feature_df["weighted_score"] = (
        feature_df["value"].abs() * feature_df["importance"]
    )

    top_features = feature_df.sort_values(
        by="weighted_score",
        ascending=False
    ).head(5)

    payload = {
        "match_id": str(sample_meta["match_id"]),
        "date": str(sample_meta["date"].date()),
        "team": sample_meta["team"],
        "opponent": sample_meta["opponent"],
        "venue": sample_meta["venue"],
        "predicted_win_probability": round(sample_prob, 4),
        "top_features": top_features.to_dict(orient="records")
    }

    return payload


if __name__ == "__main__":
    payload = build_explanation_payload(sample_index=0)
    print(payload)