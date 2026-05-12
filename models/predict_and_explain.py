import os
import json
import joblib
import pandas as pd
import numpy as np

from .predict_match_input import build_match_input, feature_cols

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "..", "models", "match_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "..", "models", "scaler.pkl")
FEATURE_IMPORTANCE_PATH = os.path.join(BASE_DIR, "..", "processed", "feature_importance.csv")


# =========================================
# Load model + scaler + feature importance
# =========================================

model = joblib.load(MODEL_PATH)

scaler = None
if os.path.exists(SCALER_PATH):
    scaler = joblib.load(SCALER_PATH)

feature_importance_df = None
if os.path.exists(FEATURE_IMPORTANCE_PATH):
    feature_importance_df = pd.read_csv(FEATURE_IMPORTANCE_PATH)


# =========================================
# Get top feature drivers
# =========================================

def get_top_features(match_input_df, top_n=10):

    if feature_importance_df is None:
        return []

    fi = feature_importance_df.copy()
    values = []

    for _, row in fi.iterrows():
        f = row["feature"]
        if f not in match_input_df.columns:
            continue

        val = match_input_df.iloc[0][f]

        values.append({
            "feature": f,
            "value": float(val) if pd.notna(val) else 0.0,
            "importance": row["importance"],
            "weighted": abs(float(val)) * row["importance"] if pd.notna(val) else 0.0
        })

    values_df = pd.DataFrame(values)
    values_df = values_df.sort_values("weighted", ascending=False)

    return values_df.head(top_n).to_dict(orient="records")


# =========================================
# Prediction + explanation
# =========================================

def predict_and_explain(team, opponent, venue):

    # build_match_input returns a fully imputed, NaN-free DataFrame
    match_input_df = build_match_input(team, opponent, venue)

    X = match_input_df[feature_cols]

    # Safety net — should never trigger after imputation in build_match_input
    if X.isnull().values.any():
        X = X.fillna(0.0)

    if scaler is not None:
        X_transformed = scaler.transform(X)
    else:
        X_transformed = X.values

    probs = model.predict_proba(X_transformed)[0]

    team_prob = float(probs[1])
    opp_prob = float(probs[0])

    prediction = {
        "team": team,
        "opponent": opponent,
        "venue": venue,
        "team_win_probability": team_prob,
        "opponent_win_probability": opp_prob,
        "top_features": get_top_features(match_input_df)
    }

    explanation = generate_explanation(team, opponent, venue, prediction)

    return {
        "prediction": prediction,
        "explanation": explanation
    }


# =========================================
# Text explanation
# =========================================

def generate_explanation(team, opponent, venue, prediction):

    team_prob = prediction["team_win_probability"]
    opp_prob = prediction["opponent_win_probability"]

    winner = team if team_prob > opp_prob else opponent

    top_features = prediction["top_features"]

    feature_text = ", ".join(
        f"{f['feature']} ({round(f['value'], 3)})"
        for f in top_features[:5]
    )

    summary = (
        f"{winner} has higher predicted win probability "
        f"based on recent form, venue stats, and historical performance."
    )

    drivers = "Key drivers: " + feature_text

    venue_text = (
        f"Venue: {venue} also influenced the prediction "
        f"based on historical scoring patterns."
    )

    final = (
        f"Final prediction favors {winner} "
        f"with probability {round(max(team_prob, opp_prob) * 100, 2)}%."
    )

    return {
        "match_summary": summary,
        "feature_drivers": drivers,
        "venue_impact": venue_text,
        "final_explanation": final
    }


# =========================================
# Test
# =========================================

if __name__ == "__main__":

    result = predict_and_explain(
        team="Chennai Super Kings",
        opponent="Mumbai Indians",
        venue="Wankhede Stadium"
    )

    print(json.dumps(result, indent=2))