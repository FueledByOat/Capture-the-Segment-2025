# app.py
from flask import Flask, render_template, request
import sqlite3
from datetime import datetime
import utils.strava_utils as strava_utils
import importlib
import config

app = Flask(__name__)

DB_PATH = 'strava_efforts.db'


def get_segments():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT segment_id, segment_name FROM segment_efforts ORDER BY segment_name")
    segments = cur.fetchall()
    conn.close()
    return segments


def get_best_efforts(segment_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    query = '''
        SELECT athlete_name, segment_id, segment_name, MIN(elapsed_time) as best_time
        FROM segment_efforts
        WHERE segment_id = ?
        GROUP BY athlete_name, segment_id
        ORDER BY best_time ASC
    '''
    cur.execute(query, (segment_id,))
    results = cur.fetchall()
    conn.close()
    return results

def calculate_flags():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Load segment owners
    cur.execute("SELECT * FROM segment_teams")
    segment_owners = {row["segment_id"]: row["owner_team"] for row in cur.fetchall()}

    # For each segment, calculate scores
    cur.execute("SELECT DISTINCT segment_id FROM segment_efforts")
    segment_ids = [row["segment_id"] for row in cur.fetchall()]

    flags = {"North": 0, "South": 0, "STP": 0}

    for segment_id in segment_ids:
        cur.execute("""
            SELECT athlete_name, team_name, elapsed_time
            FROM segment_efforts
            WHERE segment_id = ?
        """, (segment_id,))
        rows = cur.fetchall()

        if not rows:
            continue

        # Sort by elapsed_time (fastest first)
        sorted_efforts = sorted(rows, key=lambda x: x["elapsed_time"])
        num_runners = len(sorted_efforts)

        # Assign points descending from total participants
        team_points = {}
        for i, row in enumerate(sorted_efforts):
            team = row["team_name"]
            pts = num_runners - i
            team_points[team] = team_points.get(team, 0) + pts

        if not team_points:
            continue

        # Determine winning team
        winning_team = max(team_points, key=team_points.get)
        owning_team = segment_owners.get(segment_id)

        if not owning_team:
            continue

        if winning_team == owning_team:
            flags[winning_team] += 1  # DEFEND
        else:
            flags[winning_team] += 2  # CAPTURE

    conn.close()
    return flags


@app.route('/')
def index():
    segments = get_segments()
    selected_id = request.args.get('segment_id')
    best_efforts = []
    if selected_id:
        best_efforts = get_best_efforts(int(selected_id))
    return render_template('leaderboard.html', segments=segments, efforts=best_efforts, selected_id=selected_id)

@app.route('/scoreboard')
def scoreboard():
    flag_results = calculate_flags()
    return render_template('scoreboard.html', flags=flag_results)

if __name__ == '__main__':
    app.run(debug=True)