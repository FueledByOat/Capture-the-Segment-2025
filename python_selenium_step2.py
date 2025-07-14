import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time as t
import random
import collections
from collections import defaultdict

with open("strava_cookies.json", "r") as f:
    cookies = json.load(f)

s = requests.Session()
for cookie in cookies:
    s.cookies.set(cookie['name'], cookie['value'])

replacement_map = {
    # example
    "Strava McRunner 🎩" : "stmc"
    
}

print(len(replacement_map))

# Segments grouped by team
north_segments = [31546864, 20462981, 29510789, 39523134, 24861084, 13197134, 8378497, 39523117, 4732691, 15532025] 
south_segments = [1471907, 1332276, 31142862, 39499332, 22972009, 9056731, 4824653, 1518106, 30471058, 26938538]
stp_segments = [39526612, 15898012, 17268802, 26192975, 26285065, 16403630, 24530544, 7080526, 22981622, 17314996]
# monday_dd = [37250565]
# tuesday_dd = [39505193]
# wednesday_dd = [37433791]

# All Segments
segments = north_segments + south_segments + stp_segments
test_segment = [1332276]
club_id = 123456
base_url = f'https://www.strava.com/segments/{segments}?date_range=this_week&filter=club&club_id={club_id}'
urls = [f'https://www.strava.com/segments/{segments}?date_range=this_week&filter=club&club_id={club_id}' for segment_id in segments]
test_url = [f'https://www.strava.com/segments/{segments}?date_range=this_week&filter=club&club_id={club_id}' for segment_id in test_segment]
score_limit = 100 
page_size = 25     # Strava uses pages of 25 entries

segment_name_lists = {}
tie_summary_per_segment = {}
raw_name_time_pairs = [] 

for seggie in segments:
    print(f"📊 Processing segment: {seggie}")
    entries = []  # list of (name, team_emoji, time)
    t.sleep(random.randint(2,7))
    for page in range(1, (score_limit // page_size) + 1):
        url = (
            f"https://www.strava.com/segments/{seggie}?page={page}"
            f"&date_range=this_week&filter=club&club_id={club_id}"
        )
        res = s.get(url)
        if res.status_code != 200:
            break

        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.select_one("div#results table")
        if not table:
            break

        for tr in table.select("tbody tr"):
            tds = tr.find_all("td")
            if len(tds) < 6:
                continue

            name_cell = tds[1]
            date_cell = tds[2]
            time_cell = tds[-1]
            name_raw = name_cell.get_text(strip=True)
            emoji = ""
            for symbol in ["🎩", "🧢", "⛑️"]:
                if symbol in name_raw:
                    emoji = symbol
                    break
            time_val = time_cell.get_text(strip=True)
            date_val = date_cell.get_text(strip=True)
            if "Charlie Smith 🪖" in name_raw or "Dre Haus 🪖" in name_raw or "Henry Benson 🪖" in name_raw or "Yü Wu 🪖 " in name_raw or "David Nuetzman 🪖 " in name_raw:
                continue

            raw_name_time_pairs.append({"Segment": seggie, "Name": name_raw, "Date" : date_val, "Time": time_val})

            name = replacement_map.get(name_raw, name_raw)
            entries.append((name, emoji, time_val))

        if len(table.select("tbody tr")) < page_size:
            break

        t.sleep(random.randint(2,7))

    # Save name order
    segment_name_lists[seggie] = [name for (name, _, _) in entries]

    # ---- TIE SCORING ----
    time_groups = defaultdict(list)
    for idx, (name, emoji, time) in enumerate(entries):
        time_groups[time].append((idx, name, emoji))  # preserve order

    team_points = defaultdict(int)

    for time, group in time_groups.items():
        if len(group) > 1:
            group.sort()  # by original order
            for rank_offset, (_, _, emoji) in enumerate(group[1:], start=1):
                team_points[emoji] += rank_offset

    # Build header string like "🎩-2\n🧢-1"
    if team_points:
        sorted_summary = sorted(team_points.items(), key=lambda x: -x[1])  # sort by points
        header_str = "\n".join(f"{emoji}-{pts}" for emoji, pts in sorted_summary)
    else:
        header_str = ""

    tie_summary_per_segment[seggie] = header_str

    # raw_name_time_pairs.sort(key = lambda x: x[3]) # actually should be already sorted from the web pull...

# Normalize lengths
max_len = max(len(v) for v in segment_name_lists.values())
for seg_id in segment_name_lists:
    segment_name_lists[seg_id] += [None] * (max_len - len(segment_name_lists[seg_id]))

# Create main DF
df = pd.DataFrame(segment_name_lists)

# Add tie header row
tie_row = pd.DataFrame([tie_summary_per_segment])
final_df = pd.concat([tie_row, df], ignore_index=True)

# Leaderboard export
final_df.to_csv("leaderboard_ties_scored.csv", index=False, encoding="utf-8-sig")
print("✅ Exported with tie-based team scoring")

# Individual Times export
raw_df = pd.DataFrame(raw_name_time_pairs)
raw_df.to_csv("raw_name_time_log.csv", index=False, encoding="utf-8-sig")
print("📄 Exported raw name-time log to raw_name_time_log.csv")