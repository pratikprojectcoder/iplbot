import pandas as pd

df = pd.read_csv("processed/player_features.csv")


def squad_strength(team):

    team_df = df[df["team"] == team]

    latest = team_df.sort_values("date").groupby("player").tail(1)

    batting = latest["player_last5_runs_avg"].mean()
    bowling = latest["player_last5_wickets"].mean()

    return {
        "batting_strength": round(batting, 2),
        "bowling_strength": round(bowling, 2)
    }