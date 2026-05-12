import os
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from predict_match_input import build_match_input, feature_cols

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRAIN_DATA_PATH = os.path.join(BASE_DIR, "..", "processed", "final_match_features.csv")


def train_model():
    df = pd.read_csv(TRAIN_DATA_PATH)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df = df.dropna().drop_duplicates().reset_index(drop=True)

    split_date = "2019-01-01"
    train_df = df[df["date"] < split_date].copy()

    X_train = train_df[feature_cols]
    y_train = train_df["result_win"]

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)

    model = LogisticRegression(max_iter=3000, solver="lbfgs")
    model.fit(X_train_scaled, y_train)

    return model, scaler


def predict_match(team, opponent, venue):
    model, scaler = train_model()

    # build_match_input returns a fully imputed, NaN-free DataFrame
    match_input = build_match_input(team, opponent, venue)

    X = match_input[feature_cols]

    # Safety net
    if X.isnull().values.any():
        X = X.fillna(0.0)

    X_input_scaled = scaler.transform(X)

    win_prob = model.predict_proba(X_input_scaled)[0][1]

    result = {
        "team": team,
        "opponent": opponent,
        "venue": venue,
        "team_win_probability": round(float(win_prob), 4),
        "opponent_win_probability": round(float(1 - win_prob), 4)
    }

    return result


if __name__ == "__main__":
    result = predict_match(
        team="Chennai Super Kings",
        opponent="Royal Challengers Bangalore",
        venue="MA Chidambaram Stadium"
    )
    print(result)