import os
import json
import re
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from groq import Groq
from models.predict_and_explain import predict_and_explain
from models.predict_match_input import build_match_input

api_key = os.getenv("GROQ_API_KEY")

client = None
if api_key:
    try:
        api_key = api_key.strip().replace("\n", "").replace("\r", "")
        client = Groq(api_key=api_key)
    except Exception:
        client = None

TEAM_FEATURES_PATH = "processed/team_features.csv"
VENUE_FEATURES_PATH = "processed/venue_features.csv"
TEST_PREDICTIONS_PATH = "processed/test_predictions_with_confidence.csv"
PLAYER_FEATURES_PATH = "processed/player_features.csv"
SQUADS_2026_PATH = "processed/ipl_2026_squads.csv"


def phase_segmentation(overs_data):
    phases = {
        "powerplay": {"runs": 0, "overs": 0},
        "middle": {"runs": 0, "overs": 0},
        "death": {"runs": 0, "overs": 0}
    }

    for over in overs_data:
        over_num = over.get("over", 0)
        runs = over.get("runs", 0)

        if 1 <= over_num <= 6:
            phase = "powerplay"
        elif 7 <= over_num <= 15:
            phase = "middle"
        else:
            phase = "death"

        phases[phase]["runs"] += runs
        phases[phase]["overs"] += 1

    for phase in phases:
        overs = phases[phase]["overs"]
        runs = phases[phase]["runs"]
        phases[phase]["run_rate"] = round(runs / overs, 2) if overs else 0

    return phases


def parse_total_score(overs_data):
    return {
        "total_runs": sum(o.get("runs", 0) for o in overs_data),
        "total_wickets": sum(o.get("wickets", 0) for o in overs_data),
        "total_overs": len(overs_data)
    }


def calculate_momentum(overs_data):
    momentum = []
    cumulative = 0

    for over in overs_data:
        score = 0
        runs = over.get("runs", 0)
        wickets = over.get("wickets", 0)

        if runs >= 12:
            score += 2
        elif runs <= 4:
            score -= 1

        if wickets >= 2:
            score -= 2
        elif wickets == 1:
            score -= 1

        cumulative += score

        momentum.append({
            "over": over.get("over", 0),
            "momentum_score": cumulative
        })

    return momentum


def normalize_match_data(match_data):
    if all(k in match_data for k in ["team_a", "team_b", "team_a_overs_data", "team_b_overs_data"]):
        return match_data

    if "innings"in match_data and "info"in match_data:
        innings = match_data.get("innings", [])

        if len(innings) < 2:
            raise ValueError("Expected at least 2 innings in uploaded JSON.")

        def extract_over_data(innings_obj):
            overs_data = []

            for over_obj in innings_obj.get("overs", []):
                over_num = over_obj.get("over", 0) + 1
                deliveries = over_obj.get("deliveries", [])

                total_runs = 0
                total_wickets = 0

                for ball in deliveries:
                    total_runs += ball.get("runs", {}).get("total", 0)

                    wickets = ball.get("wickets", [])
                    if isinstance(wickets, list):
                        total_wickets += len(wickets)

                overs_data.append({
                    "over": over_num,
                    "runs": total_runs,
                    "wickets": total_wickets
                })

            return overs_data

        return {
            "team_a": innings[0].get("team", "Team A"),
            "team_b": innings[1].get("team", "Team B"),
            "team_a_overs_data": extract_over_data(innings[0]),
            "team_b_overs_data": extract_over_data(innings[1])
        }

    raise ValueError("Unsupported JSON format.")


def validate_match_data(match_data):
    required_keys = ["team_a", "team_b", "team_a_overs_data", "team_b_overs_data"]
    missing_keys = [key for key in required_keys if key not in match_data]

    if missing_keys:
        return False, missing_keys

    if not isinstance(match_data["team_a_overs_data"], list):
        return False, ["team_a_overs_data should be a list"]

    if not isinstance(match_data["team_b_overs_data"], list):
        return False, ["team_b_overs_data should be a list"]

    return True, []


def calculate_win_probability(match_data):
    team_a_overs = match_data.get("team_a_overs_data", [])
    team_b_overs = match_data.get("team_b_overs_data", [])

    if not team_a_overs or not team_b_overs:
        return {"team_a_win_probability": 50, "team_b_win_probability": 50}

    team_a = parse_total_score(team_a_overs)
    team_b = parse_total_score(team_b_overs)

    if team_a["total_overs"] == 0 or team_b["total_overs"] == 0:
        return {"team_a_win_probability": 50, "team_b_win_probability": 50}

    rr_diff = (team_a["total_runs"] / team_a["total_overs"]) - (team_b["total_runs"] / team_b["total_overs"])
    score_diff = team_a["total_runs"] - team_b["total_runs"]

    base = 50
    adjustment = (rr_diff * 8) + (score_diff * 0.4)

    team_a_prob = max(0, min(100, base + adjustment))

    return {
        "team_a_win_probability": round(team_a_prob, 2),
        "team_b_win_probability": round(100 - team_a_prob, 2)
    }


def generate_advanced_insights(match_data):
    team_a_overs = match_data.get("team_a_overs_data", [])
    team_b_overs = match_data.get("team_b_overs_data", [])

    team_a_score = parse_total_score(team_a_overs)
    team_b_score = parse_total_score(team_b_overs)

    team_a_name = match_data.get("team_a", "Team A")
    team_b_name = match_data.get("team_b", "Team B")

    return {
        "winner": team_a_name if team_a_score["total_runs"] >team_b_score["total_runs"] else team_b_name,
        "margin": abs(team_a_score["total_runs"] - team_b_score["total_runs"]),
        "team_a_phases": phase_segmentation(team_a_overs),
        "team_b_phases": phase_segmentation(team_b_overs),
        "team_a_momentum": calculate_momentum(team_a_overs),
        "team_b_momentum": calculate_momentum(team_b_overs),
        "win_probability": calculate_win_probability(match_data)
    }


def call_llm_with_schema(insights):
    if not client:
        return None

    prompt = f"""
Return ONLY valid JSON in this format:

{{
  "match_summary": "",
  "key_turning_points": "",
  "phase_analysis": "",
  "wicket_impact": "",
  "win_probability_analysis": "",
  "final_insight": ""
}}

Match Insights:
{json.dumps(insights, indent=2)}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a professional cricket analyst. Return strict JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )

        output = response.choices[0].message.content.strip()

        if not output:
            return None

        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return None

    except Exception:
        return None


def generate_fallback_summary(insights, match_data):
    winner = insights["winner"]
    margin = insights["margin"]
    win_prob = insights["win_probability"]
    team_a_name = match_data.get("team_a", "Team A")

    return {
        "match_summary": f"{winner} won the match by {margin} runs.",
        "key_turning_points": "Momentum swings were visible during key phases of the innings.",
        "phase_analysis": "Powerplay, middle overs, and death overs all had an impact on the match result.",
        "wicket_impact": "Wickets affected the scoring flow and pressure handling.",
        "win_probability_analysis": f"{team_a_name} had {win_prob['team_a_win_probability']}% estimated win probability.",
        "final_insight": "Overall result was driven by phase dominance, wickets, and momentum shifts."
    }


# =========================================
# Player Intelligence helpers
# =========================================

def load_2026_squads():
    try:
        squads_df = pd.read_csv(SQUADS_2026_PATH)
    except Exception:
        return {}

    required_cols = {"team", "player"}
    if not required_cols.issubset(set(squads_df.columns)):
        return {}

    squads_df["team"] = squads_df["team"].astype(str).str.strip()
    squads_df["player"] = squads_df["player"].astype(str).str.strip()
    squads_df = squads_df[squads_df["team"].ne("") & squads_df["player"].ne("")]

    def normalize_name(name):
        return re.sub(r"[^a-z0-9 ]+", "", str(name).lower()).strip()

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


def latest_player_rows(df):
    if df.empty:
        return df
    return df.sort_values("date").groupby("player").tail(1).copy()


def get_team_player_pool(df, team, min_players_required):
    base_df = df[df["team"] == team].copy()
    base_latest = latest_player_rows(base_df)
    base_count = base_latest["player"].nunique()

    # If no 2026 squad configured for this team, use full historical pool.
    if team not in SQUADS_2026:
        return base_latest, {
            "mode": "historical",
            "available_players": base_count,
            "required_players": min_players_required
        }

    filtered_df = apply_2026_squad_filter(base_df, team)
    filtered_latest = latest_player_rows(filtered_df)
    filtered_count = filtered_latest["player"].nunique()

    if filtered_count >= min_players_required:
        return filtered_latest, {
            "mode": "squad_2026",
            "available_players": filtered_count,
            "required_players": min_players_required
        }

    # Fallback when the squad file is incomplete/mismatched for this team.
    return base_latest, {
        "mode": "fallback_historical",
        "available_players": base_count,
        "required_players": min_players_required,
        "matched_squad_players": filtered_count
    }


def apply_2026_squad_filter(df, team):
    if team not in SQUADS_2026:
        return df

    team_players = SQUADS_2026[team]
    if not team_players:
        return df.iloc[0:0]

    def normalize_name(name):
        return re.sub(r"[^a-z0-9 ]+", "", str(name).lower()).strip()

    def short_name_key(name):
        parts = [p for p in normalize_name(name).split() if p]
        if not parts:
            return ""
        return f"{parts[0][0]}_{parts[-1]}"

    team_df = df.copy()
    team_df["player_norm"] = team_df["player"].apply(normalize_name)
    team_df["player_short"] = team_df["player"].apply(short_name_key)

    return team_df[
        team_df["player_norm"].isin(team_players["exact"]) |
        team_df["player_short"].isin(team_players["short"])
    ].copy()


def load_player_features():
    try:
        df = pd.read_csv(PLAYER_FEATURES_PATH)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df
    except Exception as e:
        st.error(f"Could not load player_features.csv: {e}")
        st.info("Run build_player_features.py first to generate this file.")
        return None


def predict_players(df, team, opponent, venue):
    latest, filter_info = get_team_player_pool(df, team, min_players_required=5)
    if latest.empty:
        return None

    bat_features = [
        "player_last5_runs_avg",
        "player_last5_strike_rate",
        "player_vs_team_avg",
        "player_at_venue_avg"
    ]

    bowl_features = [
        "player_last5_wickets",
        "player_last5_economy"
    ]

    # Use weighted scoring instead of ML model for direct display
    latest = latest.copy()
    latest["predicted_runs"] = (
        0.4 * latest["player_last5_runs_avg"] +
        0.3 * latest["player_vs_team_avg"] +
        0.3 * latest["player_at_venue_avg"]
    )

    latest["predicted_wickets"] = latest["player_last5_wickets"]

    top_batters = latest.sort_values("predicted_runs", ascending=False).head(5)
    top_bowlers = latest.sort_values("predicted_wickets", ascending=False).head(5)

    return {
        "top_batters": top_batters[["player", "player_last5_runs_avg", "player_last5_strike_rate", "predicted_runs"]].reset_index(drop=True),
        "top_bowlers": top_bowlers[["player", "player_last5_wickets", "player_last5_economy", "predicted_wickets"]].reset_index(drop=True),
        "filter_info": filter_info
    }


def build_best_xi(df, team):
    latest, filter_info = get_team_player_pool(df, team, min_players_required=11)
    if latest.empty:
        return None

    latest["score"] = (
        0.5 * latest["player_last5_runs_avg"] +
        0.3 * latest["player_last5_wickets"] -
        0.2 * latest["player_last5_economy"]
    )

    best_xi = latest.sort_values("score", ascending=False).head(11).reset_index(drop=True)
    best_xi.index = best_xi.index + 1

    return {
        "best_xi": best_xi[["player", "player_last5_runs_avg", "player_last5_wickets", "player_last5_economy", "score"]],
        "filter_info": filter_info
    }


def season_leaders(df):
    if SQUADS_2026:
        pooled = []
        fallback_teams = []
        # Only consider teams that are in the 2026 squad file,
        # so defunct/renamed teams (Deccan Chargers, etc.) are excluded.
        teams_to_consider = sorted(SQUADS_2026.keys())

        for team_name in teams_to_consider:
            team_latest, info = get_team_player_pool(df, team_name, min_players_required=5)
            if not team_latest.empty:
                pooled.append(team_latest)
            if info.get("mode") == "fallback_historical":
                fallback_teams.append(team_name)

        latest = pd.concat(pooled, ignore_index=True) if pooled else pd.DataFrame(columns=df.columns)
    else:
        latest = latest_player_rows(df)
        fallback_teams = []

    orange_cap = latest.sort_values("player_last5_runs_avg", ascending=False).head(10).reset_index(drop=True)
    orange_cap.index = orange_cap.index + 1

    purple_cap = latest.sort_values("player_last5_wickets", ascending=False).head(10).reset_index(drop=True)
    purple_cap.index = purple_cap.index + 1

    return {
        "orange_cap": orange_cap[["player", "team", "player_last5_runs_avg", "player_last5_strike_rate"]],
        "purple_cap": purple_cap[["player", "team", "player_last5_wickets", "player_last5_economy"]],
        "fallback_teams": fallback_teams
    }


def squad_strength(df, team):
    latest, filter_info = get_team_player_pool(df, team, min_players_required=8)
    if latest.empty:
        return None

    batting = latest["player_last5_runs_avg"].mean()
    bowling = latest["player_last5_wickets"].mean()
    strike_rate = latest["player_last5_strike_rate"].mean()
    economy = latest["player_last5_economy"].mean()

    return {
        "batting_strength": round(batting, 2),
        "bowling_strength": round(bowling, 2),
        "avg_strike_rate": round(strike_rate, 2),
        "avg_economy": round(economy, 2),
        "squad_size": len(latest),
        "filter_info": filter_info
    }


# =========================================
# App layout
# =========================================

st.set_page_config(page_title="T20 Match Intelligence System", layout="wide")
st.title("AI Cricket Match Intelligence System")

app_mode = st.sidebar.radio(
    "Choose Mode",
    ["Scorecard Explainer", "Match Outcome Predictor", "Player Intelligence", "Hand Cricket"]
)

# =========================================
# MODE 1: Scorecard Explainer
# =========================================

if app_mode == "Scorecard Explainer":
    uploaded_file = st.file_uploader("Upload Match JSON File", type="json")

    if not uploaded_file:
        st.warning("Please upload a match JSON file.")
        st.stop()

    try:
        raw_data = json.load(uploaded_file)
        match_data = normalize_match_data(raw_data)
    except Exception as e:
        st.error(f"Invalid or unsupported JSON file: {e}")
        st.stop()

    st.subheader("Normalized JSON Keys")
    st.write(list(match_data.keys()))

    is_valid, issues = validate_match_data(match_data)

    if not is_valid:
        st.error("Uploaded JSON format is incorrect.")
        st.write("Missing / Invalid fields:")
        st.write(issues)
        st.info("Expected keys: team_a, team_b, team_a_overs_data, team_b_overs_data")
        st.stop()

    if st.button("Generate Match Analysis"):
        try:
            insights = generate_advanced_insights(match_data)
        except Exception as e:
            st.error(f"Error while generating insights: {e}")
            st.stop()

        with st.spinner("Generating Analysis..."):
            analysis = call_llm_with_schema(insights)

            if analysis is None:
                analysis = generate_fallback_summary(insights, match_data)
                st.warning("Using rule-based analysis (AI unavailable).")

        st.success("Analysis Generated Successfully!")

        st.subheader("Match Summary")
        st.write(analysis.get("match_summary", "No summary available."))

        st.subheader("Key Turning Points")
        st.write(analysis.get("key_turning_points", "No turning points available."))

        st.subheader("Phase Comparison")

        phases = ["powerplay", "middle", "death"]
        team_a_runs = [insights["team_a_phases"][p]["runs"] for p in phases]
        team_b_runs = [insights["team_b_phases"][p]["runs"] for p in phases]

        fig, ax = plt.subplots()
        x = range(len(phases))

        ax.bar(x, team_a_runs, width=0.4, label=match_data["team_a"])
        ax.bar([i + 0.4 for i in x], team_b_runs, width=0.4, label=match_data["team_b"])

        ax.set_xticks([i + 0.2 for i in x])
        ax.set_xticklabels([p.title() for p in phases])
        ax.set_ylabel("Runs")
        ax.legend()

        st.pyplot(fig)

        st.subheader("Momentum Analysis")

        fig2, ax2 = plt.subplots()

        ax2.plot(
            [o["over"] for o in insights["team_a_momentum"]],
            [o["momentum_score"] for o in insights["team_a_momentum"]],
            label=match_data["team_a"]
        )

        ax2.plot(
            [o["over"] for o in insights["team_b_momentum"]],
            [o["momentum_score"] for o in insights["team_b_momentum"]],
            label=match_data["team_b"]
        )

        ax2.set_xlabel("Over")
        ax2.set_ylabel("Momentum Score")
        ax2.legend()

        st.pyplot(fig2)

        st.subheader("Win Probability")

        win_prob = insights["win_probability"]

        st.write(f"{match_data['team_a']} Win Probability")
        st.progress(int(win_prob["team_a_win_probability"]))

        st.write(f"{match_data['team_b']} Win Probability")
        st.progress(int(win_prob["team_b_win_probability"]))

        st.subheader("Final Insight")
        st.write(analysis.get("final_insight", "No final insight available."))

# =========================================
# MODE 2: Match Outcome Predictor
# =========================================

elif app_mode == "Match Outcome Predictor":
    try:
        team_df = pd.read_csv(TEAM_FEATURES_PATH)
        venue_df = pd.read_csv(VENUE_FEATURES_PATH)
    except Exception as e:
        st.error(f"Error loading CSV files: {e}")
        st.stop()

    st.subheader("Model Test Accuracy Review")

    try:
        test_pred_df = pd.read_csv(TEST_PREDICTIONS_PATH)

        total_matches = len(test_pred_df)
        correct_predictions = int(test_pred_df["correct_prediction"].sum())
        overall_accuracy = correct_predictions / total_matches if total_matches >0 else 0
        avg_confidence = test_pred_df["prediction_confidence_pct"].mean() if total_matches >0 else 0

        col_a, col_b, col_c, col_d = st.columns(4)

        with col_a:
            st.metric("Total Test Matches", total_matches)

        with col_b:
            st.metric("Correct Predictions", correct_predictions)

        with col_c:
            st.metric("Overall Test Accuracy", f"{overall_accuracy * 100:.2f}%")

        with col_d:
            st.metric("Average Confidence", f"{avg_confidence:.2f}%")

        st.subheader("Accuracy by Confidence Level")

        conf_60 = test_pred_df[test_pred_df["prediction_confidence_pct"] >60]
        conf_70 = test_pred_df[test_pred_df["prediction_confidence_pct"] >70]
        conf_80 = test_pred_df[test_pred_df["prediction_confidence_pct"] >80]

        c1, c2, c3 = st.columns(3)

        with c1:
            acc_60 = conf_60["correct_prediction"].mean() * 100 if len(conf_60) >0 else 0
            st.metric("Confidence >60%", f"{acc_60:.2f}%")
            st.caption(f"{len(conf_60)} matches")

        with c2:
            acc_70 = conf_70["correct_prediction"].mean() * 100 if len(conf_70) >0 else 0
            st.metric("Confidence >70%", f"{acc_70:.2f}%")
            st.caption(f"{len(conf_70)} matches")

        with c3:
            acc_80 = conf_80["correct_prediction"].mean() * 100 if len(conf_80) >0 else 0
            st.metric("Confidence >80%", f"{acc_80:.2f}%")
            st.caption(f"{len(conf_80)} matches")

        st.subheader("Sample Test Predictions")
        st.dataframe(
            test_pred_df[[
                "date",
                "team",
                "opponent",
                "venue",
                "predicted_winner",
                "actual_winner",
                "prediction_confidence_pct",
                "correct_prediction"
            ]].head(20)
        )

    except Exception as e:
        st.warning(f"Could not load test accuracy review file: {e}")
        st.info("Run train_match_model.py first to generate test_predictions_with_confidence.csv")

    teams = sorted(team_df["team"].dropna().unique().tolist())
    venues = sorted(venue_df["venue"].dropna().unique().tolist())

    col1, col2, col3 = st.columns(3)

    with col1:
        team = st.selectbox("Select Team", teams)

    with col2:
        opponent_options = [t for t in teams if t != team]
        opponent = st.selectbox("Select Opponent", opponent_options)

    with col3:
        venue = st.selectbox("Select Venue", venues)

    if st.button("Generate Prediction"):
        try:
            with st.spinner("Running model and generating explanation..."):
                result = predict_and_explain(team, opponent, venue)
                match_input_df = build_match_input(team, opponent, venue)

            prediction = result["prediction"]
            explanation = result["explanation"]

            team_prob = prediction["team_win_probability"] * 100
            opp_prob = prediction["opponent_win_probability"] * 100

            st.success("Prediction generated successfully")

            st.subheader("Win Probability")

            st.write(f"**{team}**: {team_prob:.2f}%")
            st.progress(int(team_prob))

            st.write(f"**{opponent}**: {opp_prob:.2f}%")
            st.progress(int(opp_prob))

            st.subheader("Batting First Feature View")

            bf_team = match_input_df.iloc[0]["team_batting_first_win_pct"]
            bf_opp = match_input_df.iloc[0]["opp_batting_first_win_pct"]
            bf_diff = match_input_df.iloc[0]["batting_first_win_pct_diff"]

            b1, b2, b3 = st.columns(3)

            with b1:
                st.metric(
                    f"{team} Batting-First Win %",
                    f"{bf_team * 100:.2f}%"if pd.notna(bf_team) else "N/A"
                )

            with b2:
                st.metric(
                    f"{opponent} Batting-First Win %",
                    f"{bf_opp * 100:.2f}%"if pd.notna(bf_opp) else "N/A"
                )

            with b3:
                st.metric(
                    "Batting-First Win % Diff",
                    f"{bf_diff * 100:.2f}%"if pd.notna(bf_diff) else "N/A"
                )

            st.caption(
                "This feature is computed from each team's historical win percentage in matches where they batted first, using only past matches."
            )

            st.subheader("Home Ground Feature View")

            home_team = match_input_df.iloc[0]["team_home_win_pct"]
            home_opp = match_input_df.iloc[0]["opp_home_win_pct"]
            home_diff = match_input_df.iloc[0]["home_win_pct_diff"]

            h1, h2, h3 = st.columns(3)

            with h1:
                st.metric(
                    f"{team} Home Win %",
                    f"{home_team * 100:.2f}%"if pd.notna(home_team) else "N/A"
                )

            with h2:
                st.metric(
                    f"{opponent} Home Win %",
                    f"{home_opp * 100:.2f}%"if pd.notna(home_opp) else "N/A"
                )

            with h3:
                st.metric(
                    "Home Win % Diff",
                    f"{home_diff * 100:.2f}%"if pd.notna(home_diff) else "N/A"
                )

            st.caption(
                "This feature is computed from each team's historical win percentage in matches played at its home ground, using only past matches."
            )

            st.subheader("Head-to-Head Feature View")

            h2h_team = match_input_df.iloc[0]["team_h2h_win_pct"]
            h2h_opp = match_input_df.iloc[0]["opp_h2h_win_pct"]
            h2h_diff = match_input_df.iloc[0]["h2h_win_pct_diff"]

            hh1, hh2, hh3 = st.columns(3)

            with hh1:
                st.metric(
                    f"{team} H2H Win %",
                    f"{h2h_team * 100:.2f}%"if pd.notna(h2h_team) else "N/A"
                )

            with hh2:
                st.metric(
                    f"{opponent} H2H Win %",
                    f"{h2h_opp * 100:.2f}%"if pd.notna(h2h_opp) else "N/A"
                )

            with hh3:
                st.metric(
                    "H2H Win % Diff",
                    f"{h2h_diff * 100:.2f}%"if pd.notna(h2h_diff) else "N/A"
                )

            st.caption(
                "This feature is computed from historical head-to-head results between the two teams, using only past matches."
            )

            st.subheader("Toss Win Feature View")

            toss_team = match_input_df.iloc[0]["team_toss_win_pct"]
            toss_opp = match_input_df.iloc[0]["opp_toss_win_pct"]
            toss_diff = match_input_df.iloc[0]["toss_win_pct_diff"]

            t1, t2, t3 = st.columns(3)

            with t1:
                st.metric(
                    f"{team} Toss-Win Match Win %",
                    f"{toss_team * 100:.2f}%"if pd.notna(toss_team) else "N/A"
                )

            with t2:
                st.metric(
                    f"{opponent} Toss-Win Match Win %",
                    f"{toss_opp * 100:.2f}%"if pd.notna(toss_opp) else "N/A"
                )

            with t3:
                st.metric(
                    "Toss Win % Diff",
                    f"{toss_diff * 100:.2f}%"if pd.notna(toss_diff) else "N/A"
                )

            st.caption(
                "This shows how often a team won the match in its past matches where it had won the toss."
            )

            st.subheader("Toss + Batting First Feature View")

            toss_bf_team = match_input_df.iloc[0]["team_toss_batting_first_win_pct"]
            toss_bf_opp = match_input_df.iloc[0]["opp_toss_batting_first_win_pct"]
            toss_bf_diff = match_input_df.iloc[0]["toss_batting_first_win_pct_diff"]

            tb1, tb2, tb3 = st.columns(3)

            with tb1:
                st.metric(
                    f"{team} Toss+Bat First Win %",
                    f"{toss_bf_team * 100:.2f}%"if pd.notna(toss_bf_team) else "N/A"
                )

            with tb2:
                st.metric(
                    f"{opponent} Toss+Bat First Win %",
                    f"{toss_bf_opp * 100:.2f}%"if pd.notna(toss_bf_opp) else "N/A"
                )

            with tb3:
                st.metric(
                    "Toss+Bat First Diff",
                    f"{toss_bf_diff * 100:.2f}%"if pd.notna(toss_bf_diff) else "N/A"
                )

            st.caption(
                "This shows historical win percentage in matches where the team won the toss and batted first."
            )

            st.subheader("Toss + Chase Feature View")

            toss_chase_team = match_input_df.iloc[0]["team_toss_chase_win_pct"]
            toss_chase_opp = match_input_df.iloc[0]["opp_toss_chase_win_pct"]
            toss_chase_diff = match_input_df.iloc[0]["toss_chase_win_pct_diff"]

            tc1, tc2, tc3 = st.columns(3)

            with tc1:
                st.metric(
                    f"{team} Toss+Chase Win %",
                    f"{toss_chase_team * 100:.2f}%"if pd.notna(toss_chase_team) else "N/A"
                )

            with tc2:
                st.metric(
                    f"{opponent} Toss+Chase Win %",
                    f"{toss_chase_opp * 100:.2f}%"if pd.notna(toss_chase_opp) else "N/A"
                )

            with tc3:
                st.metric(
                    "Toss+Chase Diff",
                    f"{toss_chase_diff * 100:.2f}%"if pd.notna(toss_chase_diff) else "N/A"
                )

            st.caption(
                "This shows historical win percentage in matches where the team won the toss and chased."
            )

            st.subheader("Toss + Venue Feature View")

            toss_venue_team = match_input_df.iloc[0]["team_toss_venue_win_pct"]
            toss_venue_opp = match_input_df.iloc[0]["opp_toss_venue_win_pct"]
            toss_venue_diff = match_input_df.iloc[0]["toss_venue_win_pct_diff"]

            tv1, tv2, tv3 = st.columns(3)

            with tv1:
                st.metric(
                    f"{team} Toss+Venue Win %",
                    f"{toss_venue_team * 100:.2f}%"if pd.notna(toss_venue_team) else "N/A"
                )

            with tv2:
                st.metric(
                    f"{opponent} Toss+Venue Win %",
                    f"{toss_venue_opp * 100:.2f}%"if pd.notna(toss_venue_opp) else "N/A"
                )

            with tv3:
                st.metric(
                    "Toss+Venue Diff",
                    f"{toss_venue_diff * 100:.2f}%"if pd.notna(toss_venue_diff) else "N/A"
                )

            st.caption(
                "This shows historical win percentage at the selected venue in matches where the team won the toss."
            )

            st.subheader("Selected Feature Values")
            feature_view_df = pd.DataFrame({
                "Feature": [
                    "team_batting_first_win_pct",
                    "opp_batting_first_win_pct",
                    "batting_first_win_pct_diff",
                    "team_home_win_pct",
                    "opp_home_win_pct",
                    "home_win_pct_diff",
                    "team_h2h_win_pct",
                    "opp_h2h_win_pct",
                    "h2h_win_pct_diff",
                    "team_toss_win_pct",
                    "opp_toss_win_pct",
                    "toss_win_pct_diff",
                    "team_toss_batting_first_win_pct",
                    "opp_toss_batting_first_win_pct",
                    "toss_batting_first_win_pct_diff",
                    "team_toss_chase_win_pct",
                    "opp_toss_chase_win_pct",
                    "toss_chase_win_pct_diff",
                    "team_toss_venue_win_pct",
                    "opp_toss_venue_win_pct",
                    "toss_venue_win_pct_diff"
                ],
                "Value": [
                    bf_team,
                    bf_opp,
                    bf_diff,
                    home_team,
                    home_opp,
                    home_diff,
                    h2h_team,
                    h2h_opp,
                    h2h_diff,
                    toss_team,
                    toss_opp,
                    toss_diff,
                    toss_bf_team,
                    toss_bf_opp,
                    toss_bf_diff,
                    toss_chase_team,
                    toss_chase_opp,
                    toss_chase_diff,
                    toss_venue_team,
                    toss_venue_opp,
                    toss_venue_diff
                ]
            })
            st.dataframe(feature_view_df)

            st.subheader("Top Feature Drivers")
            feature_df = pd.DataFrame(prediction["top_features"])
            st.dataframe(feature_df)

            st.subheader("Match Summary")
            st.write(explanation["match_summary"])

            st.subheader("Feature Drivers")
            st.write(explanation["feature_drivers"])

            st.subheader("Venue Impact")
            st.write(explanation["venue_impact"])

            st.subheader("Final Explanation")
            st.write(explanation["final_explanation"])

        except Exception as e:
            st.error(f"Prediction error: {e}")

# =========================================
# MODE 3: Player Intelligence
# =========================================

elif app_mode == "Player Intelligence":

    st.subheader("Player Intelligence")

    player_df = load_player_features()

    if player_df is None:
        st.stop()

    if SQUADS_2026:
        available_teams = set(player_df["team"].dropna().unique().tolist())
        teams_available = sorted([t for t in SQUADS_2026.keys() if t in available_teams])
        if not teams_available:
            teams_available = sorted(player_df["team"].dropna().unique().tolist())
            st.warning("2026 squads file found, but team names did not match player data.")
    else:
        teams_available = sorted(player_df["team"].dropna().unique().tolist())

    player_sub_mode = st.radio(
        "Select Analysis",
        [
            "Player Performance Predictions",
            "Best XI Builder",
            "Season Leaders (Orange & Purple Cap)",
            "Squad Strength Analysis"
        ],
        horizontal=True
    )

    # ------------------------------------------
    # Sub-mode 1: Player Performance Predictions
    # ------------------------------------------
    if player_sub_mode == "Player Performance Predictions":

        st.markdown("#### Predicted Top Batters & Bowlers for a Matchup")

        venue_options = ["Any venue"] + sorted(player_df["venue"].dropna().astype(str).unique().tolist())

        col1, col2, col3 = st.columns(3)

        with col1:
            team = st.selectbox("Select Team", teams_available, key="pp_team")

        with col2:
            opponent_options = [t for t in teams_available if t != team]
            opponent = st.selectbox("Select Opponent", opponent_options, key="pp_opp")

        with col3:
            venue = st.selectbox("Select Venue (optional)", venue_options, key="pp_venue")

        if st.button("Predict Player Performance"):
            with st.spinner("Calculating player predictions..."):
                selected_venue = None if venue == "Any venue"else venue
                result = predict_players(player_df, team, opponent, selected_venue)

            if result is None:
                st.error(f"No player data found for team: {team}")
            else:
                filter_info = result.get("filter_info", {})
                if filter_info.get("mode") == "fallback_historical":
                    st.warning(
                        f"2026 squad mapping for {team} matched only {filter_info.get('matched_squad_players', 0)} "
                        f"players (< {filter_info.get('required_players', 5)}). Showing historical player pool for stability."
                    )

                col_bat, col_bowl = st.columns(2)

                with col_bat:
                    st.markdown(f"** Top Predicted Batters — {team}**")
                    bat_df = result["top_batters"].copy()
                    bat_df.index = bat_df.index + 1
                    bat_df.columns = ["Player", "Last 5 Runs Avg", "Last 5 SR", "Predicted Runs"]
                    bat_df["Predicted Runs"] = bat_df["Predicted Runs"].round(1)
                    bat_df["Last 5 Runs Avg"] = bat_df["Last 5 Runs Avg"].round(1)
                    bat_df["Last 5 SR"] = bat_df["Last 5 SR"].round(1)
                    st.dataframe(bat_df, use_container_width=True)

                with col_bowl:
                    st.markdown(f"** Top Predicted Bowlers — {team}**")
                    bowl_df = result["top_bowlers"].copy()
                    bowl_df.index = bowl_df.index + 1
                    bowl_df.columns = ["Player", "Last 5 Wickets Avg", "Last 5 Economy", "Predicted Wickets"]
                    bowl_df["Predicted Wickets"] = bowl_df["Predicted Wickets"].round(2)
                    bowl_df["Last 5 Economy"] = bowl_df["Last 5 Economy"].round(2)
                    st.dataframe(bowl_df, use_container_width=True)

                st.caption(
                    "Predicted Runs = weighted average of last-5 runs, vs-opponent avg, and at-venue avg. "
                    "Predicted Wickets = last-5 wickets rolling average."
                )

    # ------------------------------------------
    # Sub-mode 2: Best XI Builder
    # ------------------------------------------
    elif player_sub_mode == "Best XI Builder":

        st.markdown("#### Best XI for a Team based on Recent Form")

        team = st.selectbox("Select Team", teams_available, key="xi_team")

        if st.button("Build Best XI"):
            with st.spinner("Building Best XI..."):
                xi_result = build_best_xi(player_df, team)

            if xi_result is None:
                st.error(f"No player data found for team: {team}")
            else:
                xi_df = xi_result["best_xi"]
                filter_info = xi_result.get("filter_info", {})
                if filter_info.get("mode") == "fallback_historical":
                    st.warning(
                        f"2026 squad mapping for {team} matched only {filter_info.get('matched_squad_players', 0)} "
                        f"players (< {filter_info.get('required_players', 11)}). Showing best XI from historical pool."
                    )

                st.markdown(f"** Best XI — {team}**")
                xi_df = xi_df.copy()
                xi_df.columns = ["Player", "Last 5 Runs Avg", "Last 5 Wickets", "Last 5 Economy", "Selection Score"]
                xi_df["Selection Score"] = xi_df["Selection Score"].round(2)
                xi_df["Last 5 Runs Avg"] = xi_df["Last 5 Runs Avg"].round(1)
                xi_df["Last 5 Wickets"] = xi_df["Last 5 Wickets"].round(2)
                xi_df["Last 5 Economy"] = xi_df["Last 5 Economy"].round(2)
                st.dataframe(xi_df, use_container_width=True)

                st.caption(
                    "Selection Score = 0.5 × Last-5 Runs Avg + 0.3 × Last-5 Wickets − 0.2 × Last-5 Economy. "
                    "Top 11 players by score are selected."
                )

                # Bar chart of selection scores
                fig, ax = plt.subplots(figsize=(8, 4))
                ax.barh(xi_df["Player"][::-1], xi_df["Selection Score"][::-1], color="steelblue")
                ax.set_xlabel("Selection Score")
                ax.set_title(f"Best XI Selection Scores — {team}")
                plt.tight_layout()
                st.pyplot(fig)

    # ------------------------------------------
    # Sub-mode 3: Season Leaders
    # ------------------------------------------
    elif player_sub_mode == "Season Leaders (Orange & Purple Cap)":

        st.markdown("####  Season Leaders based on Recent Rolling Form")

        with st.spinner("Computing season leaders..."):
            leaders = season_leaders(player_df)

        if leaders.get("fallback_teams"):
            st.warning(
                "Some teams had low 2026 squad match coverage and were auto-fallbacked to historical pool: "
                + ", ".join(sorted(leaders["fallback_teams"]))
            )

        col_orange, col_purple = st.columns(2)

        with col_orange:
            st.markdown("** Orange Cap — Top Run Scorers (Last-5 Avg)**")
            oc = leaders["orange_cap"].copy()
            oc.columns = ["Player", "Team", "Last 5 Runs Avg", "Last 5 SR"]
            oc["Last 5 Runs Avg"] = oc["Last 5 Runs Avg"].round(1)
            oc["Last 5 SR"] = oc["Last 5 SR"].round(1)
            st.dataframe(oc, use_container_width=True)

        with col_purple:
            st.markdown("** Purple Cap — Top Wicket Takers (Last-5 Avg)**")
            pc = leaders["purple_cap"].copy()
            pc.columns = ["Player", "Team", "Last 5 Wickets", "Last 5 Economy"]
            pc["Last 5 Wickets"] = pc["Last 5 Wickets"].round(2)
            pc["Last 5 Economy"] = pc["Last 5 Economy"].round(2)
            st.dataframe(pc, use_container_width=True)

        st.caption(
            "Rankings are based on the most recent rolling last-5 match averages per player, not cumulative season totals."
        )

        # Orange cap bar chart
        oc_plot = leaders["orange_cap"].copy()
        if oc_plot.empty:
            st.info("No Orange Cap data available for current filters.")
        else:
            fig3, ax3 = plt.subplots(figsize=(8, 4))
            ax3.barh(oc_plot["player"][::-1], oc_plot["player_last5_runs_avg"][::-1], color="darkorange")
            ax3.set_xlabel("Last 5 Runs Avg")
            ax3.set_title("Orange Cap — Top 10 Batters")
            plt.tight_layout()
            st.pyplot(fig3)

        # Purple cap bar chart
        pc_plot = leaders["purple_cap"].copy()
        if pc_plot.empty:
            st.info("No Purple Cap data available for current filters.")
        else:
            fig4, ax4 = plt.subplots(figsize=(8, 4))
            ax4.barh(pc_plot["player"][::-1], pc_plot["player_last5_wickets"][::-1], color="mediumpurple")
            ax4.set_xlabel("Last 5 Wickets Avg")
            ax4.set_title("Purple Cap — Top 10 Bowlers")
            plt.tight_layout()
            st.pyplot(fig4)

    # ------------------------------------------
    # Sub-mode 4: Squad Strength Analysis
    # ------------------------------------------
    elif player_sub_mode == "Squad Strength Analysis":

        st.markdown("####  Squad Strength Comparison")

        col1, col2 = st.columns(2)

        with col1:
            team_a = st.selectbox("Select Team A", teams_available, key="sq_team_a")

        with col2:
            team_b_options = [t for t in teams_available if t != team_a]
            team_b = st.selectbox("Select Team B", team_b_options, key="sq_team_b")

        if st.button("Compare Squad Strength"):
            with st.spinner("Analysing squads..."):
                strength_a = squad_strength(player_df, team_a)
                strength_b = squad_strength(player_df, team_b)

            if strength_a is None:
                st.error(f"No data found for {team_a}")
            elif strength_b is None:
                st.error(f"No data found for {team_b}")
            else:
                info_a = strength_a.get("filter_info", {})
                info_b = strength_b.get("filter_info", {})
                if info_a.get("mode") == "fallback_historical"or info_b.get("mode") == "fallback_historical":
                    st.warning(
                        "One or both teams had low 2026 squad coverage; historical pool fallback was applied for reliable comparison."
                    )

                st.markdown("#### Squad Metrics Comparison")

                metrics = ["batting_strength", "bowling_strength", "avg_strike_rate", "avg_economy"]
                labels = ["Batting Strength\n(Avg Runs)", "Bowling Strength\n(Avg Wickets)", "Avg Strike Rate", "Avg Economy"]

                m1, m2, m3, m4 = st.columns(4)

                for col, metric, label in zip([m1, m2, m3, m4], metrics, labels):
                    val_a = strength_a[metric]
                    val_b = strength_b[metric]
                    delta = round(val_a - val_b, 2)
                    with col:
                        st.metric(
                            label=f"{label}",
                            value=f"{team_a}: {val_a}",
                            delta=f"vs {team_b}: {val_b}  (Δ {delta:+.2f})"
                        )

                # Radar-style bar chart comparison
                fig5, ax5 = plt.subplots(figsize=(8, 4))

                x = range(len(metrics))
                vals_a = [strength_a[m] for m in metrics]
                vals_b = [strength_b[m] for m in metrics]

                ax5.bar([i - 0.2 for i in x], vals_a, width=0.4, label=team_a, color="steelblue")
                ax5.bar([i + 0.2 for i in x], vals_b, width=0.4, label=team_b, color="tomato")
                ax5.set_xticks(list(x))
                ax5.set_xticklabels(["Batting", "Bowling", "Strike Rate", "Economy"], fontsize=9)
                ax5.set_ylabel("Value")
                ax5.set_title("Squad Strength Comparison")
                ax5.legend()
                plt.tight_layout()
                st.pyplot(fig5)

                # Squad size
                st.info(
                    f"{team_a} squad size (players with data): {strength_a['squad_size']}  |  "
                    f"{team_b} squad size (players with data): {strength_b['squad_size']}"
                )

                st.caption(
                    "All metrics are based on each player's most recent last-5 match rolling average. "
                    "Lower Economy is better for bowling."
                )

# =========================================
# MODE 4: Hand Cricket Game
# =========================================

elif app_mode == "Hand Cricket":
    import random
    import time
    import base64
    from pathlib import Path

    # ---- Load images as base64 ----
    def load_image_b64(path):
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            return ""

    IMG_BATSMAN = load_image_b64("static/images/batsman.png")
    IMG_BOWLER = load_image_b64("static/images/bowler.png")
    IMG_WICKET = load_image_b64("static/images/wicket.png")

    # ---- IPL Team Config ----
    IPL_TEAMS = {
        "Chennai Super Kings": {"short": "CSK", "color": "#FFCB05"},
        "Mumbai Indians": {"short": "MI", "color": "#004BA0"},
        "Royal Challengers Bengaluru": {"short": "RCB", "color": "#D4213D"},
        "Kolkata Knight Riders": {"short": "KKR", "color": "#3A225D"},
        "Delhi Capitals": {"short": "DC", "color": "#004C93"},
        "Rajasthan Royals": {"short": "RR", "color": "#EA1A85"},
        "Punjab Kings": {"short": "PBKS", "color": "#DD1F2D"},
        "Sunrisers Hyderabad": {"short": "SRH", "color": "#F26522"},
        "Gujarat Titans": {"short": "GT", "color": "#1C1C1C"},
        "Lucknow Super Giants": {"short": "LSG", "color": "#A72056"},
    }

    # ---- Custom CSS for game styling ----
    st.markdown("""
    <style>
    .cricket-title {
        text-align: center;
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #FFD700, #FF6B35, #E91E63);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .cricket-subtitle {
        text-align: center;
        color: #9CA3AF;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    .scoreboard {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .score-big {
        font-size: 3rem;
        font-weight: 900;
        color: #FFD700;
        text-align: center;
        text-shadow: 0 0 20px rgba(255,215,0,0.3);
    }
    .score-label {
        font-size: 0.9rem;
        color: #9CA3AF;
        text-align: center;
    }
    .ball-result {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 48px; height: 48px;
        border-radius: 50%;
        font-weight: 800;
        font-size: 1.2rem;
        margin: 4px;
    }
    .ball-run { background: linear-gradient(135deg, #10B981, #059669); color: white; }
    .ball-dot { background: linear-gradient(135deg, #6B7280, #4B5563); color: white; }
    .ball-four { background: linear-gradient(135deg, #3B82F6, #2563EB); color: white; }
    .ball-six { background: linear-gradient(135deg, #F59E0B, #D97706); color: white; }
    .ball-out { background: linear-gradient(135deg, #EF4444, #DC2626); color: white; }
    .commentary-box {
        background: rgba(255,255,255,0.05);
        border-left: 4px solid #FFD700;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
        font-style: italic;
        color: #E5E7EB;
    }
    .vs-badge {
        text-align: center;
        font-size: 1.5rem;
        font-weight: 900;
        color: #FFD700;
        padding: 0.5rem;
    }
    .target-banner {
        text-align: center;
        background: linear-gradient(90deg, #7C3AED, #DB2777);
        color: white;
        padding: 0.8rem;
        border-radius: 12px;
        font-size: 1.1rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }
    .winner-banner {
        text-align: center;
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 50%, #FF6347 100%);
        color: #1a1a2e;
        padding: 1.5rem;
        border-radius: 16px;
        font-size: 1.8rem;
        font-weight: 900;
        margin: 1rem 0;
        box-shadow: 0 8px 32px rgba(255,215,0,0.3);
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="cricket-title">IPL Hand Cricket</div>', unsafe_allow_html=True)
    st.markdown('<div class="cricket-subtitle">Pick a number 1-6 • Match with the AI and you\'re OUT!</div>', unsafe_allow_html=True)

    # ---- Session state initialization ----
    def init_game_state():
        return {
            "phase": "setup",          # setup | toss | playing | innings_break | result
            "user_team": None,
            "cpu_team": None,
            "toss_winner": None,
            "user_batting": None,      # True if user bats first
            "innings": 1,
            "current_batting": None,   # "user"or "cpu"
            # Innings tracking
            "innings1_runs": 0,
            "innings1_wickets": 0,
            "innings1_balls": 0,
            "innings1_log": [],
            "innings2_runs": 0,
            "innings2_wickets": 0,
            "innings2_balls": 0,
            "innings2_log": [],
            # Current innings helpers
            "runs": 0,
            "wickets": 0,
            "balls": 0,
            "ball_log": [],
            "target": None,
            "max_overs": 5,
            "max_wickets": 3,
            "last_commentary": "",
            "game_over": False,
            "winner": None,
        }

    if "hc"not in st.session_state:
        st.session_state.hc = init_game_state()

    hc = st.session_state.hc

    # ---- Commentary generator ----
    def get_commentary(user_num, cpu_num, runs, is_out, batting_team_short):
        if is_out:
            return random.choice([
                f"WICKET! Both picked {user_num}! The batter has to walk back!",
                f"OUT! Same number {user_num}! What a moment in this match!",
                f"GONE! Matched at {user_num}! The fielding side celebrates!",
                f"BOWLED! Both chose {user_num}! Huge wicket for the bowling side!",
            ])
        if runs == 6:
            return random.choice([
                f"SIX! {batting_team_short} smashes it out of the park! Massive hit!",
                f"MAXIMUM! That's gone into the stands! 6 runs!",
                f"What a shot! That's sailed over the boundary for SIX!",
            ])
        if runs == 4:
            return random.choice([
                f"FOUR! Beautifully timed through the gap! {batting_team_short} scoring freely!",
                f"Boundary! Pierces the field and races to the rope! 4 runs!",
                f"FOUR! Cracking shot! That's pure class!",
            ])
        if runs == 0:
            return random.choice([
                "Dot ball! Tight bowling, no run scored.",
                "Good delivery! The batter couldn't get it away.",
            ])
        return random.choice([
            f"{runs} run{'s'if runs >1 else ''}! Good cricket from {batting_team_short}.",
            f"{runs} added to the total. Smart batting!",
            f"{runs} run{'s'if runs >1 else ''} off that delivery.",
        ])

    # ---- Helper: overs display  ----
    def overs_display(balls):
        return f"{balls // 6}.{balls % 6}"

    # ========= PHASE: SETUP =========
    if hc["phase"] == "setup":
        st.markdown("---")
        st.markdown("###  Match Setup")

        col_setup1, col_setup2 = st.columns(2)

        with col_setup1:
            team_names = list(IPL_TEAMS.keys())
            user_team = st.selectbox("Pick Your Team", team_names, key="hc_user_team")

        with col_setup2:
            overs = st.selectbox("Overs Per Innings", [2, 3, 5, 10], index=2, key="hc_overs")

        wickets = st.selectbox("Wickets Per Innings", [1, 2, 3, 5, 10], index=2, key="hc_wickets")

        if st.button("Start Match", use_container_width=True):
            cpu_options = [t for t in IPL_TEAMS if t != user_team]
            cpu_team = random.choice(cpu_options)
            hc.update(init_game_state())
            hc["user_team"] = user_team
            hc["cpu_team"] = cpu_team
            hc["max_overs"] = overs
            hc["max_wickets"] = wickets
            hc["phase"] = "toss"
            st.rerun()

    # ========= PHASE: TOSS =========
    elif hc["phase"] == "toss":
        st.markdown("---")
        user_info = IPL_TEAMS[hc["user_team"]]
        cpu_info = IPL_TEAMS[hc["cpu_team"]]

        st.markdown(f"""
        <div class="scoreboard">
            <div style="display:flex;justify-content:center;align-items:center;gap:2rem;">
                <div style="text-align:center;">
                    <div style="font-size:2.5rem;">{user_info['short']}</div>
                    <div style="color:#FFD700;font-weight:700;font-size:1.2rem;">{user_info['short']}</div>
                    <div style="color:#9CA3AF;font-size:0.8rem;">You</div>
                </div>
                <div class="vs-badge">VS</div>
                <div style="text-align:center;">
                    <div style="font-size:2.5rem;">{cpu_info['short']}</div>
                    <div style="color:#FFD700;font-weight:700;font-size:1.2rem;">{cpu_info['short']}</div>
                    <div style="color:#9CA3AF;font-size:0.8rem;">CPU</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("###  Toss Time!")
        toss_call = st.radio("Call the toss:", ["Heads", "Tails"], horizontal=True, key="hc_toss_call")

        if st.button("Flip the Coin!", use_container_width=True):
            result = random.choice(["Heads", "Tails"])
            user_won_toss = (toss_call == result)
            hc["toss_winner"] = "user"if user_won_toss else "cpu"

            if user_won_toss:
                st.success(f"It's **{result}**! You won the toss!")
            else:
                st.error(f"It's **{result}**! {IPL_TEAMS[hc['cpu_team']]['short']} won the toss!")
                cpu_choice = random.choice(["bat", "bowl"])
                hc["user_batting"] = (cpu_choice == "bowl")
                hc["current_batting"] = "user"if hc["user_batting"] else "cpu"
                hc["phase"] = "playing"
                st.info(f"{IPL_TEAMS[hc['cpu_team']]['short']} chose to **{cpu_choice}** first!")
                st.rerun()

        if hc["toss_winner"] == "user"and hc["user_batting"] is None:
            st.markdown("#### What do you choose?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Bat First", use_container_width=True):
                    hc["user_batting"] = True
                    hc["current_batting"] = "user"
                    hc["phase"] = "playing"
                    st.rerun()
            with c2:
                if st.button("Bowl First", use_container_width=True):
                    hc["user_batting"] = False
                    hc["current_batting"] = "cpu"
                    hc["phase"] = "playing"
                    st.rerun()

    # ========= PHASE: PLAYING =========
    elif hc["phase"] == "playing":
        user_info = IPL_TEAMS[hc["user_team"]]
        cpu_info = IPL_TEAMS[hc["cpu_team"]]
        batting_team = hc["user_team"] if hc["current_batting"] == "user"else hc["cpu_team"]
        bowling_team = hc["cpu_team"] if hc["current_batting"] == "user"else hc["user_team"]
        bat_info = IPL_TEAMS[batting_team]
        is_user_batting = (hc["current_batting"] == "user")

        # ---- Scoreboard ----
               
        st.markdown(f"""
        <div class="scoreboard">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="text-align:center;flex:1;">
                    <div style="color:#9CA3AF;font-size:0.8rem;">{'BATTING'if is_user_batting else 'BOWLING'}</div>
                    <div style="font-size:1.5rem;">{user_info['short']}</div>
                </div>
                <div style="text-align:center;flex:2;">
                    <div class="score-label">INNINGS {hc['innings']} • {bat_info['short']} Batting</div>
                    <div class="score-big">{hc['runs']}/{hc['wickets']}</div>
                    <div class="score-label">Overs: {overs_display(hc['balls'])} / {hc['max_overs']}.0</div>
                </div>
                <div style="text-align:center;flex:1;">
                    <div style="color:#9CA3AF;font-size:0.8rem;">{'BOWLING'if is_user_batting else 'BATTING'}</div>
                    <div style="font-size:1.5rem;">{cpu_info['short']}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Target banner (2nd innings)
        if hc["target"] is not None:
            need = hc["target"] - hc["runs"]
            balls_left = (hc["max_overs"] * 6) - hc["balls"]
            if need >0:
                rrr = round((need / balls_left) * 6, 2) if balls_left >0 else 999
                st.markdown(f'<div class="target-banner">Target: {hc["target"]} | Need {need} from {balls_left} balls | RRR: {rrr}</div>', unsafe_allow_html=True)

        # Ball log display
        if hc["ball_log"]:
            this_over_balls = hc["ball_log"][-(hc["balls"] % 6 if hc["balls"] % 6 != 0 else 6):]
            ball_html = "<div style='text-align:center;margin:0.5rem 0;'>"
            for b in hc["ball_log"][-12:]:  # show last 12 balls
                if b == "W":
                    ball_html += '<span class="ball-result ball-out">W</span>'
                elif b == 6:
                    ball_html += '<span class="ball-result ball-six">6</span>'
                elif b == 4:
                    ball_html += '<span class="ball-result ball-four">4</span>'
                elif b == 0:
                    ball_html += '<span class="ball-result ball-dot">•</span>'
                else:
                    ball_html += f'<span class="ball-result ball-run">{b}</span>'
            ball_html += "</div>"
            st.markdown(ball_html, unsafe_allow_html=True)

        # Commentary
        if hc["last_commentary"]:
            st.markdown(f'<div class="commentary-box">{hc["last_commentary"]}</div>', unsafe_allow_html=True)

        # ---- Check if innings is over ----
        innings_over = False
        if hc["balls"] >= hc["max_overs"] * 6:
            innings_over = True
        if hc["wickets"] >= hc["max_wickets"]:
            innings_over = True
        if hc["target"] is not None and hc["runs"] >= hc["target"]:
            innings_over = True

        if innings_over and not hc["game_over"]:
            if hc["innings"] == 1:
                # Save innings 1 data
                hc["innings1_runs"] = hc["runs"]
                hc["innings1_wickets"] = hc["wickets"]
                hc["innings1_balls"] = hc["balls"]
                hc["innings1_log"] = hc["ball_log"].copy()
                # Setup innings 2
                hc["target"] = hc["runs"] + 1
                hc["innings"] = 2
                hc["runs"] = 0
                hc["wickets"] = 0
                hc["balls"] = 0
                hc["ball_log"] = []
                hc["last_commentary"] = ""
                hc["current_batting"] = "cpu"if hc["current_batting"] == "user"else "user"
                hc["phase"] = "innings_break"
                st.rerun()
            else:
                # Save innings 2 & determine winner
                hc["innings2_runs"] = hc["runs"]
                hc["innings2_wickets"] = hc["wickets"]
                hc["innings2_balls"] = hc["balls"]
                hc["innings2_log"] = hc["ball_log"].copy()
                hc["game_over"] = True

                first_bat = hc["user_team"] if hc["user_batting"] else hc["cpu_team"]
                second_bat = hc["cpu_team"] if hc["user_batting"] else hc["user_team"]

                if hc["innings2_runs"] >= hc["target"]:
                    hc["winner"] = second_bat
                elif hc["innings1_runs"] >hc["innings2_runs"]:
                    hc["winner"] = first_bat
                else:
                    hc["winner"] = "Tie"

                hc["phase"] = "result"
                st.rerun()

        # ---- Play input ----
        if not innings_over:
            if is_user_batting:
                st.markdown("###  You're Batting — Pick your shot!")
                cols = st.columns(6)
                for i, col in enumerate(cols):
                    with col:
                        if st.button(f"{i+1}", key=f"hc_bat_{i+1}", use_container_width=True):
                            user_num = i + 1
                            cpu_num = random.randint(1, 6)
                            is_out = (user_num == cpu_num)
                            if is_out:
                                hc["wickets"] += 1
                                hc["balls"] += 1
                                hc["ball_log"].append("W")
                            else:
                                hc["runs"] += user_num
                                hc["balls"] += 1
                                hc["ball_log"].append(user_num)
                            hc["last_commentary"] = get_commentary(user_num, cpu_num, user_num, is_out, bat_info["short"])
                            st.rerun()
            else:
                st.markdown("###  You're Bowling — Pick your delivery!")
                cols = st.columns(6)
                for i, col in enumerate(cols):
                    with col:
                        if st.button(f"{i+1}", key=f"hc_bowl_{i+1}", use_container_width=True):
                            user_num = i + 1
                            cpu_num = random.randint(1, 6)
                            is_out = (user_num == cpu_num)
                            if is_out:
                                hc["wickets"] += 1
                                hc["balls"] += 1
                                hc["ball_log"].append("W")
                            else:
                                hc["runs"] += cpu_num
                                hc["balls"] += 1
                                hc["ball_log"].append(cpu_num)
                            hc["last_commentary"] = get_commentary(user_num, cpu_num, cpu_num, is_out, bat_info["short"])
                            st.rerun()

    # ========= PHASE: INNINGS BREAK =========
    elif hc["phase"] == "innings_break":
        user_info = IPL_TEAMS[hc["user_team"]]
        cpu_info = IPL_TEAMS[hc["cpu_team"]]
        first_bat = hc["user_team"] if hc["user_batting"] else hc["cpu_team"]
        first_bat_info = IPL_TEAMS[first_bat]

        st.markdown(f"""
        <div class="scoreboard">
            <div style="text-align:center;">
                <div style="color:#FFD700;font-size:1rem;font-weight:600;">INNINGS BREAK</div>
                <div style="color:#E5E7EB;font-size:1.2rem;margin:0.5rem 0;">
                    {first_bat_info['short']} scored
                </div>
                <div class="score-big">{hc['innings1_runs']}/{hc['innings1_wickets']}</div>
                <div class="score-label">in {overs_display(hc['innings1_balls'])} overs</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        second_bat = hc["cpu_team"] if hc["user_batting"] else hc["user_team"]
        second_info = IPL_TEAMS[second_bat]
        st.markdown(f'<div class="target-banner">{second_info["short"]} need {hc["target"]} runs to win in {hc["max_overs"]} overs</div>', unsafe_allow_html=True)

        if st.button("Start 2nd Innings", use_container_width=True):
            hc["phase"] = "playing"
            st.rerun()

    # ========= PHASE: RESULT =========
    elif hc["phase"] == "result":
        user_info = IPL_TEAMS[hc["user_team"]]
        cpu_info = IPL_TEAMS[hc["cpu_team"]]
        first_bat = hc["user_team"] if hc["user_batting"] else hc["cpu_team"]
        second_bat = hc["cpu_team"] if hc["user_batting"] else hc["user_team"]
        first_info = IPL_TEAMS[first_bat]
        second_info = IPL_TEAMS[second_bat]

        # Winner banner
        if hc["winner"] == "Tie":
            st.markdown('<div class="winner-banner">It\'s a TIE! What a match!</div>', unsafe_allow_html=True)
        else:
            winner_info = IPL_TEAMS[hc["winner"]]
            is_user_winner = (hc["winner"] == hc["user_team"])

            if hc["winner"] == second_bat:
                wickets_left = hc["max_wickets"] - hc["innings2_wickets"]
                margin = f"by {wickets_left} wicket{'s'if wickets_left != 1 else ''}"
            else:
                margin = f"by {hc['innings1_runs'] - hc['innings2_runs']} runs"

            banner_text = f"{hc['winner']} wins {margin}!"
            st.markdown(f'<div class="winner-banner">{banner_text}</div>', unsafe_allow_html=True)

            if is_user_winner:
                st.balloons()

        # Scorecard
        st.markdown("###  Match Scorecard")

        col_sc1, col_sc2 = st.columns(2)

        with col_sc1:
            st.markdown(f"""
            <div class="scoreboard">
                <div style="text-align:center;">
                    <div style="color:#9CA3AF;font-size:0.8rem;">1st INNINGS</div>
                    <div style="font-size:1.3rem;">{first_info['short']}</div>
                    <div class="score-big">{hc['innings1_runs']}/{hc['innings1_wickets']}</div>
                    <div class="score-label">({overs_display(hc['innings1_balls'])} overs)</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_sc2:
            st.markdown(f"""
            <div class="scoreboard">
                <div style="text-align:center;">
                    <div style="color:#9CA3AF;font-size:0.8rem;">2nd INNINGS</div>
                    <div style="font-size:1.3rem;">{second_info['short']}</div>
                    <div class="score-big">{hc['innings2_runs']}/{hc['innings2_wickets']}</div>
                    <div class="score-label">({overs_display(hc['innings2_balls'])} overs)</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Ball-by-ball logs
        with st.expander("1st Innings Ball Log"):
            if hc["innings1_log"]:
                ball_html = ""
                for b in hc["innings1_log"]:
                    if b == "W":
                        ball_html += '<span class="ball-result ball-out">W</span>'
                    elif b == 6:
                        ball_html += '<span class="ball-result ball-six">6</span>'
                    elif b == 4:
                        ball_html += '<span class="ball-result ball-four">4</span>'
                    elif b == 0:
                        ball_html += '<span class="ball-result ball-dot">•</span>'
                    else:
                        ball_html += f'<span class="ball-result ball-run">{b}</span>'
                st.markdown(ball_html, unsafe_allow_html=True)

        with st.expander("2nd Innings Ball Log"):
            if hc["innings2_log"]:
                ball_html = ""
                for b in hc["innings2_log"]:
                    if b == "W":
                        ball_html += '<span class="ball-result ball-out">W</span>'
                    elif b == 6:
                        ball_html += '<span class="ball-result ball-six">6</span>'
                    elif b == 4:
                        ball_html += '<span class="ball-result ball-four">4</span>'
                    elif b == 0:
                        ball_html += '<span class="ball-result ball-dot">•</span>'
                    else:
                        ball_html += f'<span class="ball-result ball-run">{b}</span>'
                st.markdown(ball_html, unsafe_allow_html=True)

        # Play again
        st.markdown("---")
        if st.button("Play Again", use_container_width=True):
            st.session_state.hc = init_game_state()
            st.rerun()