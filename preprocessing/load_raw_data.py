import json
import os

DATA_PATH = "ipl_json"

matches = []

for file in os.listdir(DATA_PATH):

    if file.endswith(".json"):

        file_path = os.path.join(DATA_PATH, file)

        with open(file_path, "r") as f:
            match_data = json.load(f)
            matches.append(match_data)

print("Total matches loaded:", len(matches))