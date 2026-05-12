import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor

DATA_PATH = "processed/player_features.csv"
MODEL_PATH = "models/bowling_model.pkl"

df = pd.read_csv(DATA_PATH)

features = [
    "player_last5_wickets",
    "player_last5_economy",
]

target = "wickets"

X = df[features]
y = df[target]

model = RandomForestRegressor(
    n_estimators=200,
    max_depth=8,
    random_state=42
)

model.fit(X, y)

joblib.dump(model, MODEL_PATH)

print("Bowling model trained")