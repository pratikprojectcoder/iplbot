import json
import os
import pandas as pd

DATA_PATH = "ipl_json"
OUTPUT_PATH = "processed/matches_clean.csv"

match_rows = []

for file in os.listdir(DATA_PATH):
    if file.endswith(".json"):
        file_path = os.path.join(DATA_PATH, file)

        with open(file_path, "r", encoding="utf-8") as f:
            match = json.load(f)

        info = match.get("info", {})

        match_id = file.replace(".json", "")

        dates = info.get("dates", [])
        match_date = dates[0] if dates else None

        teams = info.get("teams", [])
        team_a = teams[0] if len(teams) > 0 else None
        team_b = teams[1] if len(teams) > 1 else None

        venue = info.get("venue", None)
        city = info.get("city", None)

        toss = info.get("toss", {})
        toss_winner = toss.get("winner", None)
        toss_decision = toss.get("decision", None)

        outcome = info.get("outcome", {})
        winner = outcome.get("winner", None)

        result_type = None
        margin = None

        by = outcome.get("by", {})
        if "runs" in by:
            result_type = "runs"
            margin = by["runs"]
        elif "wickets" in by:
            result_type = "wickets"
            margin = by["wickets"]
        elif "result" in outcome:
            result_type = outcome.get("result")
            margin = None

        match_rows.append({
            "match_id": match_id,
            "date": match_date,
            "team_a": team_a,
            "team_b": team_b,
            "venue": venue,
            "city": city,
            "toss_winner": toss_winner,
            "toss_decision": toss_decision,
            "winner": winner,
            "result_type": result_type,
            "margin": margin
        })

df = pd.DataFrame(match_rows)

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.sort_values("date").reset_index(drop=True)
os.makedirs("processed", exist_ok=True)
df.to_csv(OUTPUT_PATH, index=False)

print("matches_clean.csv created successfully")
print("Total matches:", len(df))
print(df.head())