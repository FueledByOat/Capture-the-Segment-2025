from flask import Flask, render_template, request, send_file
import csv
import io
import os
from dotenv import load_dotenv

# Import components
from database import get_db_connection
from auth_blueprint import auth_bp

# Load environment variables
load_dotenv()

app = Flask(__name__)
# A secret key is required for the session cookie used in the auth flow
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

# Register the authentication blueprint
app.register_blueprint(auth_bp)


def get_segments():
    conn = get_db_connection()
    # RealDictCursor lets you access columns by name
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT DISTINCT segment_id, segment_name FROM segment_efforts ORDER BY segment_name")
    segments = cur.fetchall()
    cur.close()
    conn.close()
    return segments

def get_best_efforts(segment_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    query = '''
        SELECT athlete_name, segment_id, segment_name, MIN(elapsed_time) as best_time
        FROM segment_efforts
        WHERE segment_id = %s
        GROUP BY athlete_name, segment_id, segment_name
        ORDER BY best_time ASC
    '''
    cur.execute(query, (segment_id,))
    rows = cur.fetchall()

    results = []
    num_runners = len(rows)
    for i, row in enumerate(rows):
        points = num_runners - i
        result = dict(row)
        result['points'] = points
        results.append(result)
    
    cur.close()
    conn.close()
    return results

def calculate_flags():
    """
    Calculates team flag totals by joining segment efforts with the athletes table
    to determine team composition and performance on each segment.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get the designated owner team for each segment from the 'segment_teams' table
    cur.execute("SELECT segment_id, owner_team FROM segment_teams")
    segment_owners = {row["segment_id"]: row["owner_team"] for row in cur.fetchall()}

    # Get all unique segments that have at least one effort recorded
    cur.execute("SELECT DISTINCT segment_id FROM segment_efforts")
    segment_ids = [row["segment_id"] for row in cur.fetchall()]

    # Initialize flag counts for each team
    flags = {"North": 0, "South": 0, "STP": 0}

    # Process each segment individually
    for segment_id in segment_ids:
        owner_team = segment_owners.get(segment_id)
        if not owner_team:
            continue  # Skip this segment if it has no designated owner

        # This single query now fetches all efforts for the segment AND joins with the
        # 'athletes' table to get the team_name for each runner.
        query = """
            SELECT
                e.elapsed_time,
                a.team_name
            FROM
                segment_efforts e
            JOIN
                athletes a ON e.athlete_id = a.athlete_id
            WHERE
                e.segment_id = %s
        """
        cur.execute(query, (segment_id,))
        all_efforts = cur.fetchall()

        if not all_efforts:
            continue

        # Logic for "Dub" segments (awarded for most participants)
        if owner_team == "Dub":
            participation = {}
            for effort in all_efforts:
                team = effort["team_name"]
                if team:  # Ensure the athlete has a team
                    participation[team] = participation.get(team, 0) + 1
            
            if participation:
                winning_team = max(participation, key=participation.get)
                if winning_team in flags:
                    flags[winning_team] += 2  # 2 flags for the win

        # Logic for standard segments (awarded based on "True Team Scoring")
        else:
            sorted_efforts = sorted(all_efforts, key=lambda x: x["elapsed_time"])
            num_runners = len(sorted_efforts)
            team_points = {}

            for i, effort in enumerate(sorted_efforts):
                team = effort["team_name"]
                if team:  # Ensure the athlete has a team
                    points = num_runners - i
                    team_points[team] = team_points.get(team, 0) + points
            
            if team_points:
                winning_team = max(team_points, key=team_points.get)
                if winning_team == owner_team:
                    flags[winning_team] += 1  # 1 flag for a successful DEFEND
                else:
                    flags[winning_team] += 2  # 2 flags for a successful CAPTURE

    conn.close()
    return flags

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/leaderboard')
def leaderboard():
    segments = get_segments()
    selected_id = request.args.get('segment_id')
    best_efforts = [] # Initialize as empty list
    if selected_id:
        try:
            # Only calculate if a segment is selected
            best_efforts = get_best_efforts(int(selected_id))
        except (ValueError, TypeError):
            return "Invalid segment ID.", 400
    return render_template('leaderboard.html', segments=segments, efforts=best_efforts, selected_id=selected_id)

# ... (Your /scoreboard and /export/leaderboard routes remain the same) ...
@app.route('/scoreboard')
def scoreboard():
    return "Scoreboard Page"

@app.route('/export/leaderboard')
def export_leaderboard():
    return "Export Page"

if __name__ == '__main__':
    # Use the PORT environment variable if available, for services like Azure App Service
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)