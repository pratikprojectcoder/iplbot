import json
import os
import pandas as pd
from collections import defaultdict

DATA_PATH = "ipl_json"
OUTPUT_PATH = "processed/player_match_stats.csv"

# Wicket types generally credited to bowler
BOWLER_WICKET_TYPES = {
    "bowled",
    "caught",
    "caught and bowled",
    "lbw",
    "stumped",
    "hit wicket"
}


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

    outcome = info.get("outcome", {})
    winner = outcome.get("winner", None)

    # player-level accumulator for one match
    player_stats = defaultdict(lambda: {
        "team": None,
        "opponent": None,
        "batting_runs": 0,
        "balls_faced": 0,
        "fours": 0,
        "sixes": 0,
        "dismissal_kind": None,
        "out": 0,
        "balls_bowled": 0,
        "runs_conceded": 0,
        "wickets": 0
    })

    for innings_obj in innings_list:
        batting_team = innings_obj.get("team")
        innings_index = innings_list.index(innings_obj)

        if len(innings_list) >= 2:
            if innings_index == 0:
                bowling_team = innings_list[1].get("team")
            else:
                bowling_team = innings_list[0].get("team")
        else:
            bowling_team = None

        overs = innings_obj.get("overs", [])

        for over_obj in overs:
            deliveries = over_obj.get("deliveries", [])

            for delivery in deliveries:
                batter = delivery.get("batter")
                bowler = delivery.get("bowler")
                runs = delivery.get("runs", {})
                batter_runs = runs.get("batter", 0)
                total_runs = runs.get("total", 0)

                # -------------------------
                # Batting stats
                # -------------------------
                if batter:
                    player_stats[batter]["team"] = batting_team
                    player_stats[batter]["opponent"] = bowling_team
                    player_stats[batter]["batting_runs"] += batter_runs

                    if is_legal_ball(delivery):
                        player_stats[batter]["balls_faced"] += 1

                    if batter_runs == 4:
                        player_stats[batter]["fours"] += 1
                    elif batter_runs == 6:
                        player_stats[batter]["sixes"] += 1

                # -------------------------
                # Bowling stats
                # -------------------------
                if bowler:
                    player_stats[bowler]["team"] = bowling_team
                    player_stats[bowler]["opponent"] = batting_team
                    player_stats[bowler]["runs_conceded"] += total_runs

                    if is_legal_ball(delivery):
                        player_stats[bowler]["balls_bowled"] += 1

                # -------------------------
                # Wickets
                # -------------------------
                wickets = delivery.get("wickets", [])
                for wicket in wickets:
                    player_out = wicket.get("player_out")
                    kind = wicket.get("kind")

                    if player_out:
                        player_stats[player_out]["dismissal_kind"] = kind
                        player_stats[player_out]["out"] = 1

                    if bowler and kind in BOWLER_WICKET_TYPES:
                        player_stats[bowler]["wickets"] += 1

    # Convert player stats dict to rows
    for player, stats in player_stats.items():
        balls_bowled = stats["balls_bowled"]
        overs_bowled = f"{balls_bowled // 6}.{balls_bowled % 6}" if balls_bowled > 0 else "0.0"

        balls_faced = stats["balls_faced"]
        batting_runs = stats["batting_runs"]

        strike_rate = round((batting_runs / balls_faced) * 100, 2) if balls_faced > 0 else 0
        economy = round((stats["runs_conceded"] / (balls_bowled / 6)), 2) if balls_bowled > 0 else 0

        rows.append({
            "match_id": match_id,
            "date": match_date,
            "player": player,
            "team": stats["team"],
            "opponent": stats["opponent"],
            "venue": venue,
            "batting_runs": batting_runs,
            "balls_faced": balls_faced,
            "fours": stats["fours"],
            "sixes": stats["sixes"],
            "strike_rate": strike_rate,
            "dismissal_kind": stats["dismissal_kind"],
            "out": stats["out"],
            "balls_bowled": balls_bowled,
            "overs_bowled": overs_bowled,
            "runs_conceded": stats["runs_conceded"],
            "wickets": stats["wickets"],
            "economy": economy,
            "won_match": 1 if stats["team"] == winner else 0
        })

df = pd.DataFrame(rows)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.sort_values(["date", "match_id", "player"]).reset_index(drop=True)

os.makedirs("processed", exist_ok=True)
df.to_csv(OUTPUT_PATH, index=False)

print("player_match_stats.csv created successfully")
print("Total rows:", len(df))
print(df.head())