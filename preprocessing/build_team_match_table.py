import json
import os
import pandas as pd

DATA_PATH = "ipl_json"
OUTPUT_PATH = "processed/team_match_stats.csv"


def get_phase(over_number):
    # Cricsheet JSON uses 0-based over numbers
    if 0 <= over_number <= 5:
        return "powerplay"
    elif 6 <= over_number <= 14:
        return "middle"
    else:
        return "death"


def is_legal_ball(delivery):
    extras = delivery.get("extras", {})
    return "wides" not in extras and "noballs" not in extras


def parse_innings_stats(innings_obj):
    team = innings_obj.get("team")

    total_runs = 0
    total_wickets = 0
    total_balls = 0

    powerplay_runs = 0
    powerplay_wickets = 0

    middle_runs = 0
    middle_wickets = 0

    death_runs = 0
    death_wickets = 0

    overs_list = innings_obj.get("overs", [])

    for over_obj in overs_list:
        over_num = over_obj.get("over")
        phase = get_phase(over_num)

        for delivery in over_obj.get("deliveries", []):
            runs_total = delivery.get("runs", {}).get("total", 0)
            total_runs += runs_total

            if is_legal_ball(delivery):
                total_balls += 1

            wickets = delivery.get("wickets", [])
            wicket_count = len(wickets)
            total_wickets += wicket_count

            if phase == "powerplay":
                powerplay_runs += runs_total
                powerplay_wickets += wicket_count
            elif phase == "middle":
                middle_runs += runs_total
                middle_wickets += wicket_count
            else:
                death_runs += runs_total
                death_wickets += wicket_count

    overs_faced = round(total_balls / 6, 2) if total_balls > 0 else 0
    run_rate = round(total_runs / overs_faced, 2) if overs_faced > 0 else 0

    return {
        "team": team,
        "runs_scored": total_runs,
        "wickets_lost": total_wickets,
        "balls_faced": total_balls,
        "overs_faced": overs_faced,
        "run_rate": run_rate,
        "powerplay_runs": powerplay_runs,
        "powerplay_wickets_lost": powerplay_wickets,
        "middle_runs": middle_runs,
        "middle_wickets_lost": middle_wickets,
        "death_runs": death_runs,
        "death_wickets_lost": death_wickets
    }


rows = []

for file in os.listdir(DATA_PATH):
    if not file.endswith(".json"):
        continue

    file_path = os.path.join(DATA_PATH, file)

    with open(file_path, "r", encoding="utf-8") as f:
        match = json.load(f)

    info = match.get("info", {})
    innings = match.get("innings", [])

    if len(innings) < 2:
        continue

    match_id = file.replace(".json", "")
    dates = info.get("dates", [])
    match_date = dates[0] if dates else None

    venue = info.get("venue")
    toss = info.get("toss", {})
    toss_winner = toss.get("winner")
    toss_decision = toss.get("decision")

    outcome = info.get("outcome", {})
    winner = outcome.get("winner")

    innings1 = parse_innings_stats(innings[0])
    innings2 = parse_innings_stats(innings[1])

    team1 = innings1["team"]
    team2 = innings2["team"]

    row1 = {
        "match_id": match_id,
        "date": match_date,
        "team": team1,
        "opponent": team2,
        "venue": venue,
        "toss_winner": toss_winner,
        "toss_decision": toss_decision,
        "toss_won": 1 if toss_winner == team1 else 0,
        "innings": 1,
        "batted_first": 1,
        "runs_scored": innings1["runs_scored"],
        "wickets_lost": innings1["wickets_lost"],
        "balls_faced": innings1["balls_faced"],
        "overs_faced": innings1["overs_faced"],
        "run_rate": innings1["run_rate"],
        "powerplay_runs": innings1["powerplay_runs"],
        "powerplay_wickets_lost": innings1["powerplay_wickets_lost"],
        "middle_runs": innings1["middle_runs"],
        "middle_wickets_lost": innings1["middle_wickets_lost"],
        "death_runs": innings1["death_runs"],
        "death_wickets_lost": innings1["death_wickets_lost"],
        "result_win": 1 if winner == team1 else 0,
        "target": None,
        "chased_successfully": 0,
        "opponent_runs": innings2["runs_scored"],
        "opponent_wickets": innings2["wickets_lost"]
    }

    row2 = {
        "match_id": match_id,
        "date": match_date,
        "team": team2,
        "opponent": team1,
        "venue": venue,
        "toss_winner": toss_winner,
        "toss_decision": toss_decision,
        "toss_won": 1 if toss_winner == team2 else 0,
        "innings": 2,
        "batted_first": 0,
        "runs_scored": innings2["runs_scored"],
        "wickets_lost": innings2["wickets_lost"],
        "balls_faced": innings2["balls_faced"],
        "overs_faced": innings2["overs_faced"],
        "run_rate": innings2["run_rate"],
        "powerplay_runs": innings2["powerplay_runs"],
        "powerplay_wickets_lost": innings2["powerplay_wickets_lost"],
        "middle_runs": innings2["middle_runs"],
        "middle_wickets_lost": innings2["middle_wickets_lost"],
        "death_runs": innings2["death_runs"],
        "death_wickets_lost": innings2["death_wickets_lost"],
        "result_win": 1 if winner == team2 else 0,
        "target": innings1["runs_scored"] + 1,
        "chased_successfully": 1 if winner == team2 else 0,
        "opponent_runs": innings1["runs_scored"],
        "opponent_wickets": innings1["wickets_lost"]
    }

    rows.append(row1)
    rows.append(row2)

df = pd.DataFrame(rows)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.sort_values(["date", "match_id", "innings"]).reset_index(drop=True)

os.makedirs("processed", exist_ok=True)
df.to_csv(OUTPUT_PATH, index=False)

print("team_match_stats.csv created successfully")
print("Total rows:", len(df))
print(df.head())