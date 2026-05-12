import pandas as pd

df = pd.read_csv("processed/player_features.csv")


def season_leaders():

    latest = df.sort_values("date").groupby("player").tail(1)

    orange_cap = latest.sort_values("player_last5_runs_avg", ascending=False).head(10)
    purple_cap = latest.sort_values("player_last5_wickets", ascending=False).head(10)

    return {
        "orange_cap": orange_cap[["player", "player_last5_runs_avg"]].to_dict("records"),
        "purple_cap": purple_cap[["player", "player_last5_wickets"]].to_dict("records")
    }