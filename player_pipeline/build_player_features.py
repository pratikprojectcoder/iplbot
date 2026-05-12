import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(BASE_DIR, "..", "processed", "player_match_table.csv")
OUTPUT_PATH = os.path.join(BASE_DIR, "..", "processed", "player_features.csv")

df = pd.read_csv(INPUT_PATH)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.sort_values(["player", "date"]).reset_index(drop=True)

df["player_last5_runs_avg"] = df.groupby("player")["runs"].transform(lambda x: x.shift(1).rolling(5).mean())
df["player_last5_strike_rate"] = df.groupby("player")["strike_rate"].transform(lambda x: x.shift(1).rolling(5).mean())
df["player_last5_wickets"] = df.groupby("player")["wickets"].transform(lambda x: x.shift(1).rolling(5).mean())
df["player_last5_economy"] = df.groupby("player")["economy"].transform(lambda x: x.shift(1).rolling(5).mean())
df["player_vs_team_avg"] = df.groupby(["player", "opponent"])["runs"].transform(lambda x: x.shift(1).expanding().mean())
df["player_at_venue_avg"] = df.groupby(["player", "venue"])["runs"].transform(lambda x: x.shift(1).expanding().mean())

df = df.fillna(0)

os.makedirs(os.path.join(BASE_DIR, "..", "processed"), exist_ok=True)
df.to_csv(OUTPUT_PATH, index=False)
print("player_features.csv created")
print("Total rows:", len(df))
print(df.head())