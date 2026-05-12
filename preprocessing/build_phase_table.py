import json
import os
import pandas as pd

DATA_PATH = "ipl_json"
OUTPUT_PATH = "processed/team_phase_stats.csv"


def get_phase(over_number):
    # Cricsheet uses 0-based over index
    if 0 <= over_number <= 5:
        return "powerplay"
    elif 6 <= over_number <= 14:
        return "middle"
    else:
        return "death"


def is_legal_ball(delivery):
    extras = delivery.get("extras", {})
    return "wides" not in extras and "noballs" not in extras


rows = []

for file in os.listdir(DATA_PATH):
    if not file.endswith(".json"):
        continue

    file_path = os.path.join(DATA_PATH, file)

    with open(file_path, "r", encoding="utf-8") as f:
        match = json.load(f)

    info = match.get("info", {})
    innings_list = match.get("innings", [])

    if len(innings_list) < 2:
        continue

    match_id = file.replace(".json", "")
    dates = info.get("dates", [])
    match_date = dates[0] if dates else None
    venue = info.get("venue", None)

    for innings_obj in innings_list:
        team = innings_obj.get("team")
        overs = innings_obj.get("overs", [])

        phase_data = {
            "powerplay": {"runs": 0, "wickets": 0, "balls": 0},
            "middle": {"runs": 0, "wickets": 0, "balls": 0},
            "death": {"runs": 0, "wickets": 0, "balls": 0}
        }

        for over_obj in overs:
            over_num = over_obj.get("over")
            phase = get_phase(over_num)

            for delivery in over_obj.get("deliveries", []):
                runs_total = delivery.get("runs", {}).get("total", 0)
                phase_data[phase]["runs"] += runs_total

                wickets = delivery.get("wickets", [])
                phase_data[phase]["wickets"] += len(wickets)

                if is_legal_ball(delivery):
                    phase_data[phase]["balls"] += 1

        for phase_name, stats in phase_data.items():
            balls = stats["balls"]
            overs_faced = round(balls / 6, 2) if balls > 0 else 0
            run_rate = round(stats["runs"] / overs_faced, 2) if overs_faced > 0 else 0

            rows.append({
                "match_id": match_id,
                "date": match_date,
                "team": team,
                "venue": venue,
                "phase": phase_name,
                "runs": stats["runs"],
                "wickets_lost": stats["wickets"],
                "balls": balls,
                "overs": overs_faced,
                "run_rate": run_rate
            })

df = pd.DataFrame(rows)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.sort_values(["date", "match_id", "team", "phase"]).reset_index(drop=True)

os.makedirs("processed", exist_ok=True)
df.to_csv(OUTPUT_PATH, index=False)

print("team_phase_stats.csv created successfully")
print("Total rows:", len(df))
print(df.head(10))