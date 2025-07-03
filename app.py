# app.py
from flask import Flask, render_template, request, send_file
import sqlite3
from datetime import datetime
import csv
import io
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
    rows = cur.fetchall()

    # Calculate points based on rank (True Team scoring)
    results = []
    num_runners = len(rows)
    for i, row in enumerate(rows):
        points = num_runners - i
        result = dict(row)
        result['points'] = points
        results.append(result)

    conn.close()
    return results


def calculate_flags():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM segment_teams")
    segment_owners = {row["segment_id"]: row["owner_team"] for row in cur.fetchall()}

    cur.execute("SELECT DISTINCT segment_id FROM segment_efforts")
    segment_ids = [row["segment_id"] for row in cur.fetchall()]

    flags = {"North": 0, "South": 0, "STP": 0}

    for segment_id in segment_ids:
        cur.execute("SELECT athlete_name, team_name FROM segment_efforts WHERE segment_id = ?", (segment_id,))
        rows = cur.fetchall()
        if not rows:
            continue

        owner_team = segment_owners.get(segment_id)
        if not owner_team:
            continue

        if owner_team == "Dub":
            # All-or-nothing: count participants per team
            participation = {}
            for row in rows:
                team = row["team_name"]
                participation[team] = participation.get(team, 0) + 1
            if participation:
                max_team = max(participation, key=participation.get)
                if max_team in flags:
                    flags[max_team] += 2  # 2 flags for most participants
        else:
            # True Team scoring: rank by elapsed_time
            cur.execute("SELECT athlete_name, team_name, elapsed_time FROM segment_efforts WHERE segment_id = ?", (segment_id,))
            detailed_rows = cur.fetchall()
            sorted_efforts = sorted(detailed_rows, key=lambda x: x["elapsed_time"])
            num_runners = len(sorted_efforts)
            team_points = {}
            for i, row in enumerate(sorted_efforts):
                team = row["team_name"]
                pts = num_runners - i
                team_points[team] = team_points.get(team, 0) + pts
            if team_points:
                max_team = max(team_points, key=team_points.get)
                if max_team == owner_team:
                    flags[max_team] += 1  # DEFEND
                else:
                    flags[max_team] += 2  # CAPTURE

    conn.close()
    return flags


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/leaderboard')
def leaderboard():
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


@app.route('/export/leaderboard')
def export_leaderboard():
    segment_id = request.args.get('segment_id')
    if not segment_id:
        return "No segment selected.", 400

    results = get_best_efforts(int(segment_id))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Athlete', 'Segment ID', 'Segment Name', 'Best Time', 'Points'])
    for row in results:
        writer.writerow([row['athlete_name'], row['segment_id'], row['segment_name'], row['best_time'], row['points']])

    output.seek(0)
    return send_file(io.BytesIO(output.read().encode()), mimetype='text/csv', as_attachment=True, download_name='leaderboard.csv')


if __name__ == '__main__':
    app.run(debug=True)