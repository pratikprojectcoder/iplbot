import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor

DATA_PATH = "processed/player_features.csv"
MODEL_PATH = "models/batting_model.pkl"

df = pd.read_csv(DATA_PATH)

features = [
    "player_last5_runs_avg",
    "player_last5_strike_rate",
    "player_vs_team_avg",
    "player_at_venue_avg"
]

target = "runs"

X = df[features]
y = df[target]

model = RandomForestRegressor(
    n_estimators=200,
    max_depth=8,
    random_state=42
)

model.fit(X, y)

joblib.dump(model, MODEL_PATH)

print("Batting model trained")