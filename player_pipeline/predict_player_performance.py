import pandas as pd
import joblib
import re

BAT_MODEL = joblib.load("models/batting_model.pkl")
BOWL_MODEL = joblib.load("models/bowling_model.pkl")

FEATURES_PATH = "processed/player_features.csv"
SQUADS_2026_PATH = "processed/ipl_2026_squads.csv"

df = pd.read_csv(FEATURES_PATH)

def load_2026_squads(path=SQUADS_2026_PATH):
    try:
        squads_df = pd.read_csv(path)
    except Exception:
        return {}

    required_cols = {"team", "player"}
    if not required_cols.issubset(set(squads_df.columns)):
        return {}

    squads_df["team"] = squads_df["team"].astype(str).str.strip()
    squads_df["player"] = squads_df["player"].astype(str).str.strip()
    squads_df = squads_df[squads_df["team"].ne("") & squads_df["player"].ne("")]

    def normalize_name(name):
        return re.sub(r"[^a-z0-9 ]+", " ", str(name).lower()).strip()

    def short_name_key(name):
        parts = [p for p in normalize_name(name).split() if p]
        if not parts:
            return ""
        return f"{parts[0][0]}_{parts[-1]}"

    squad_map = {}
    for team, team_rows in squads_df.groupby("team"):
        exact = set()
        short = set()
        for player in team_rows["player"].tolist():
            n = normalize_name(player)
            if n:
                exact.add(n)
                short.add(short_name_key(player))
        squad_map[team] = {"exact": exact, "short": short}

    return squad_map


SQUADS_2026 = load_2026_squads()


def predict_players(team, opponent, venue):

    team_df = df[df["team"] == team].copy()
    if team in SQUADS_2026:
        def normalize_name(name):
            return re.sub(r"[^a-z0-9 ]+", " ", str(name).lower()).strip()

        def short_name_key(name):
            parts = [p for p in normalize_name(name).split() if p]
            if not parts:
                return ""
            return f"{parts[0][0]}_{parts[-1]}"

        team_df["player_norm"] = team_df["player"].apply(normalize_name)
        team_df["player_short"] = team_df["player"].apply(short_name_key)
        team_df = team_df[
            team_df["player_norm"].isin(SQUADS_2026[team]["exact"]) |
            team_df["player_short"].isin(SQUADS_2026[team]["short"])
        ]

    latest = (
        team_df.sort_values("date")
        .groupby("player")
        .tail(1)
    )

    # Batting prediction
    bat_features = [
        "player_last5_runs_avg",
        "player_last5_strike_rate",
        "player_vs_team_avg",
        "player_at_venue_avg"
    ]

    latest["predicted_runs"] = BAT_MODEL.predict(latest[bat_features])

    # Bowling prediction
    bowl_features = [
        "player_last5_wickets",
        "player_last5_economy"
    ]

    latest["predicted_wickets"] = BOWL_MODEL.predict(latest[bowl_features])

    top_batters = latest.sort_values("predicted_runs", ascending=False).head(5)
    top_bowlers = latest.sort_values("predicted_wickets", ascending=False).head(5)

    return {
        "top_batters": top_batters[["player", "predicted_runs"]].to_dict("records"),
        "top_bowlers": top_bowlers[["player", "predicted_wickets"]].to_dict("records")
    }