import os
import joblib
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score, log_loss

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_PATH = os.path.join(BASE_DIR, "..", "processed", "final_match_features.csv")
MODEL_OUTPUT_PATH = os.path.join(BASE_DIR, "match_model.pkl")
SCALER_OUTPUT_PATH = os.path.join(BASE_DIR, "scaler.pkl")
FEATURE_IMPORTANCE_OUTPUT_PATH = os.path.join(BASE_DIR, "..", "processed", "feature_importance.csv")
PREDICTIONS_OUTPUT_PATH = os.path.join(BASE_DIR, "..", "processed", "test_predictions_with_confidence.csv")

df = pd.read_csv(DATA_PATH)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["year"] = df["date"].dt.year

df = df.dropna().drop_duplicates().reset_index(drop=True)

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

years = sorted(df["year"].dropna().unique().tolist())

if len(years) < 3:
    raise ValueError("Need data from at least 3 different years for yearly 60/20/20 split.")

n_years = len(years)
train_end = int(n_years * 0.6)
val_end = int(n_years * 0.8)

if train_end == 0:
    train_end = 1
if val_end <= train_end:
    val_end = train_end + 1
if val_end >= n_years:
    val_end = n_years - 1

train_years = years[:train_end]
val_years = years[train_end:val_end]
test_years = years[val_end:]

print("\n===== YEARLY SPLIT =====")
print("All years:", years)
print("Train years:", train_years)
print("Validation years:", val_years)
print("Test years:", test_years)

train_df = df[df["year"].isin(train_years)].copy()
val_df = df[df["year"].isin(val_years)].copy()
test_df = df[df["year"].isin(test_years)].copy()

X_train = train_df[feature_cols]
y_train = train_df["result_win"]

X_val = val_df[feature_cols]
y_val = val_df["result_win"]

X_test = test_df[feature_cols]
y_test = test_df["result_win"]

print("\nTrain size:", X_train.shape)
print("Validation size:", X_val.shape)
print("Test size:", X_test.shape)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
X_test_scaled = scaler.transform(X_test)

print("\n===== LOGISTIC REGRESSION (SCALED) =====")

lr = LogisticRegression(max_iter=3000, solver="lbfgs")
lr.fit(X_train_scaled, y_train)

y_val_pred_lr = lr.predict(X_val_scaled)
y_val_prob_lr = lr.predict_proba(X_val_scaled)[:, 1]

accuracy_val_lr = accuracy_score(y_val, y_val_pred_lr)
roc_val_lr = roc_auc_score(y_val, y_val_prob_lr)
logloss_val_lr = log_loss(y_val, y_val_prob_lr)

print("\nValidation Performance:")
print("Accuracy:", round(accuracy_val_lr, 4))
print("ROC AUC:", round(roc_val_lr, 4))
print("Log Loss:", round(logloss_val_lr, 4))

y_test_pred_lr = lr.predict(X_test_scaled)
y_test_prob_lr = lr.predict_proba(X_test_scaled)[:, 1]

accuracy_test_lr = accuracy_score(y_test, y_test_pred_lr)
roc_test_lr = roc_auc_score(y_test, y_test_prob_lr)
logloss_test_lr = log_loss(y_test, y_test_prob_lr)

print("\nTest Performance:")
print("Accuracy:", round(accuracy_test_lr, 4))
print("ROC AUC:", round(roc_test_lr, 4))
print("Log Loss:", round(logloss_test_lr, 4))

print("\n===== RANDOM FOREST =====")

rf = RandomForestClassifier(
    n_estimators=300,
    max_depth=8,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=42
)

rf.fit(X_train, y_train)

y_val_pred_rf = rf.predict(X_val)
y_val_prob_rf = rf.predict_proba(X_val)[:, 1]

accuracy_val_rf = accuracy_score(y_val, y_val_pred_rf)
roc_val_rf = roc_auc_score(y_val, y_val_prob_rf)
logloss_val_rf = log_loss(y_val, y_val_prob_rf)

print("\nValidation Performance:")
print("Accuracy:", round(accuracy_val_rf, 4))
print("ROC AUC:", round(roc_val_rf, 4))
print("Log Loss:", round(logloss_val_rf, 4))

y_test_pred_rf = rf.predict(X_test)
y_test_prob_rf = rf.predict_proba(X_test)[:, 1]

accuracy_test_rf = accuracy_score(y_test, y_test_pred_rf)
roc_test_rf = roc_auc_score(y_test, y_test_prob_rf)
logloss_test_rf = log_loss(y_test, y_test_prob_rf)

print("\nTest Performance:")
print("Accuracy:", round(accuracy_test_rf, 4))
print("ROC AUC:", round(roc_test_rf, 4))
print("Log Loss:", round(logloss_test_rf, 4))

if roc_val_lr >= roc_val_rf:
    best_model = lr
    best_model_name = "LogisticRegression"
    best_uses_scaler = True

    best_test_pred = y_test_pred_lr
    best_test_prob = y_test_prob_lr
    best_feature_importance = abs(lr.coef_[0])
else:
    best_model = rf
    best_model_name = "RandomForest"
    best_uses_scaler = False

    best_test_pred = y_test_pred_rf
    best_test_prob = y_test_prob_rf
    best_feature_importance = rf.feature_importances_

print("\n===== BEST MODEL SELECTED =====")
print("Best model:", best_model_name)

joblib.dump(best_model, MODEL_OUTPUT_PATH)

if best_uses_scaler:
    joblib.dump(scaler, SCALER_OUTPUT_PATH)
else:
    if os.path.exists(SCALER_OUTPUT_PATH):
        os.remove(SCALER_OUTPUT_PATH)

print("\nModel saved to:", MODEL_OUTPUT_PATH)
if best_uses_scaler:
    print("Scaler saved to:", SCALER_OUTPUT_PATH)
else:
    print("No scaler saved because selected model does not require scaling.")

feature_importance_df = pd.DataFrame({
    "feature": feature_cols,
    "importance": best_feature_importance
}).sort_values("importance", ascending=False)

feature_importance_df.to_csv(FEATURE_IMPORTANCE_OUTPUT_PATH, index=False)
print("Feature importance saved to:", FEATURE_IMPORTANCE_OUTPUT_PATH)

test_results_df = test_df[["match_id", "date", "team", "opponent", "venue", "result_win"]].copy()

test_results_df["predicted_label"] = best_test_pred
test_results_df["actual_label"] = y_test.values

test_results_df["team_win_probability"] = best_test_prob
test_results_df["opponent_win_probability"] = 1 - best_test_prob
test_results_df["prediction_confidence_pct"] = (
    test_results_df[["team_win_probability", "opponent_win_probability"]].max(axis=1) * 100
).round(2)

test_results_df["predicted_winner"] = test_results_df.apply(
    lambda row: row["team"] if row["predicted_label"] == 1 else row["opponent"],
    axis=1
)

test_results_df["actual_winner"] = test_results_df.apply(
    lambda row: row["team"] if row["actual_label"] == 1 else row["opponent"],
    axis=1
)

test_results_df["correct_prediction"] = (
    test_results_df["predicted_label"] == test_results_df["actual_label"]
).astype(int)

test_results_df = test_results_df[[
    "match_id",
    "date",
    "team",
    "opponent",
    "venue",
    "team_win_probability",
    "opponent_win_probability",
    "prediction_confidence_pct",
    "predicted_winner",
    "actual_winner",
    "correct_prediction"
]]

test_results_df.to_csv(PREDICTIONS_OUTPUT_PATH, index=False)
print(f"\nTest predictions with confidence saved to: {PREDICTIONS_OUTPUT_PATH}")

print("\n===== SAMPLE TEST PREDICTION =====")

sample_index = 0
sample_row = test_results_df.iloc[sample_index]

print("Match ID:", sample_row["match_id"])
print("Date:", sample_row["date"])
print("Team:", sample_row["team"])
print("Opponent:", sample_row["opponent"])
print("Venue:", sample_row["venue"])
print("Predicted Winner:", sample_row["predicted_winner"])
print("Actual Winner:", sample_row["actual_winner"])
print("Confidence %:", sample_row["prediction_confidence_pct"])
print("Correct Prediction:", sample_row["correct_prediction"])

print("\n===== SAMPLE MATCH FEATURE CONTRIBUTION =====")

sample_features = pd.DataFrame({
    "feature": feature_cols,
    "value": X_test.iloc[sample_index].values,
    "importance": best_feature_importance
})

sample_features["weighted"] = (
    sample_features["value"].abs() * sample_features["importance"]
)

sample_features = sample_features.sort_values(by="weighted", ascending=False)

print(sample_features.head(10))