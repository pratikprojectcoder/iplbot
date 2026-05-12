import pandas as pd

FEATURES_PATH = "processed/player_features.csv"

df = pd.read_csv(FEATURES_PATH)


def build_best_xi(team):

    team_df = df[df["team"] == team].copy()

    latest = team_df.sort_values("date").groupby("player").tail(1)

    latest["score"] = (
        0.5 * latest["player_last5_runs_avg"] +
        0.3 * latest["player_last5_wickets"] -
        0.2 * latest["player_last5_economy"]
    )

    best_xi = latest.sort_values("score", ascending=False).head(11)

    return best_xi[["player", "score"]].to_dict("records")