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


@app.route('/')
def index():
    segments = get_segments()
    selected_id = request.args.get('segment_id')
    best_efforts = []
    if selected_id:
        best_efforts = get_best_efforts(int(selected_id))
    return render_template('leaderboard.html', segments=segments, efforts=best_efforts, selected_id=selected_id)


if __name__ == '__main__':
    app.run(debug=True)