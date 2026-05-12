import json
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "ipl_json")
OUTPUT_PATH = os.path.join(BASE_DIR, "processed", "player_match_table.csv")

rows = []

for file in os.listdir(DATA_PATH):
    if not file.endswith(".json"):
        continue
    file_path = os.path.join(DATA_PATH, file)
    with open(file_path, "r", encoding="utf-8") as f:
        match = json.load(f)

    info = match.get("info", {})
    match_id = file.replace(".json", "")
    dates = info.get("dates", [])
    match_date = dates[0] if dates else None
    venue = info.get("venue", None)
    innings_list = match.get("innings", [])

    if len(innings_list) < 2:
        continue

    all_teams = [inn.get("team") for inn in innings_list if inn.get("team")]

    for innings in innings_list:
        batting_team = innings.get("team")
        bowling_team = next((t for t in all_teams if t != batting_team), None)
        overs = innings.get("overs", [])
        player_stats = {}

        for over in overs:
            for delivery in over.get("deliveries", []):
                batter = delivery.get("batter")
                bowler = delivery.get("bowler")
                runs = delivery.get("runs", {}).get("batter", 0)
                total_runs = delivery.get("runs", {}).get("total", 0)

                if batter:
                    if batter not in player_stats:
                        player_stats[batter] = {"team": batting_team, "opponent": bowling_team, "runs": 0, "balls": 0, "wickets": 0, "runs_conceded": 0, "balls_bowled": 0}
                    player_stats[batter]["runs"] += runs
                    player_stats[batter]["balls"] += 1

                if bowler:
                    if bowler not in player_stats:
                        player_stats[bowler] = {"team": bowling_team, "opponent": batting_team, "runs": 0, "balls": 0, "wickets": 0, "runs_conceded": 0, "balls_bowled": 0}
                    player_stats[bowler]["runs_conceded"] += total_runs
                    player_stats[bowler]["balls_bowled"] += 1

                if "wickets" in delivery:
                    for w in delivery["wickets"]:
                        if w.get("kind") != "run out" and bowler and bowler in player_stats:
                            player_stats[bowler]["wickets"] += 1

        for player, stats in player_stats.items():
            balls = stats["balls"]
            strike_rate = round((stats["runs"] / balls * 100), 2) if balls > 0 else 0
            overs_bowled = stats["balls_bowled"] / 6
            economy = round((stats["runs_conceded"] / overs_bowled), 2) if overs_bowled > 0 else 0
            rows.append({"match_id": match_id, "date": match_date, "team": stats["team"], "opponent": stats["opponent"], "venue": venue, "player": player, "runs": stats["runs"], "balls": balls, "strike_rate": strike_rate, "wickets": stats["wickets"], "economy": economy})

df = pd.DataFrame(rows)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.sort_values(["date", "player"]).reset_index(drop=True)
os.makedirs(os.path.join(BASE_DIR, "processed"), exist_ok=True)
df.to_csv(OUTPUT_PATH, index=False)
print("player_match_table.csv created successfully")
print("Total rows:", len(df))
print(df.head())