# 🏁 Capture the Segment

This project is a web-based application built with Flask and SQLite to track and score athletes' performances on Strava segments. It supports self-service Strava authentication, team-based leaderboard scoring, and weekly flag-based competition tracking.

---

## 🚀 Features

- **Leaderboard Viewer**: See ranked performances by athletes on each segment.
- **True Team Scoring**: Everyone earns points; top finishers earn more.
- **Team Flags System**:
  - 🏁 1 Flag: Successfully defend a segment your team owns.
  - 🏁🏁 2 Flags: Capture a segment owned by another team.
  - 🏁🏁 2 Flags (Dub segments): Earned by most total participants, regardless of time.
- **CSV Export**: Download segment leaderboards as CSV.
- **Simple Web Interface**: View scoreboards and leaderboards from a clean, styled UI.

---

## 🧱 Tech Stack

- Python 3
- Flask
- SQLite (now Postgres)
- HTML/CSS (templated with Jinja2)
- Strava API (OAuth2 access and activity data)
- CSV and in-browser rendering

---

## 🗂 Project Structure
```bash
Capture-the-Segment/
|
├── .github/ -- Github Actions Workflows
│   └── workflows/
│       ├── webapp-deploy.yml
│       └── function-deploy.yml
|
├── pipeline_function/ -- Azure Deployment Files
│   ├── __init__.py
│   ├── function.json
│   ├── pipeline_logic.py
│   ├── requirements.txt
│   ├── database.py
│   └── utils/
│       └── strava_utils.py
|
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── leaderboard.html
│   └── scoreboard.html
|
├── utils/
│   └── strava_utils.py
|
├── app.py
├── auth_blueprint.py
├── database.py
├── requirements.txt
├── .env
└── .gitignore
```

## ⚙️ Setup Instructions

### 1. Clone and install dependencies

```bash
git clone https://github.com/yourusername/strava-segment-tracker.git
cd strava-segment-tracker
pip install -r requirements.txt
```

2. Set up environment (Local)

Create a .env or secrets.env file with:

```bash
CLIENT_ID=your_strava_client_id
CLIENT_SECRET=your_strava_client_secret
```

You may optionally include:

```bash
DB_PATH=strava_efforts.db
```

3. Run the app

```bash
python app.py
```

Visit http://localhost:5000 in your browser.

## 🛡 Scoring Rules Summary

| Segment Owner Team | Segment Outcome     | Flags Awarded |
| ------------------ | ------------------- | ------------- |
| North/South/STP    | Defend (own win)    | 🏁 1 Flag     |
| North/South/STP    | Capture (enemy win) | 🏁🏁 2 Flags  |
| Dub (neutral)      | Most runners        | 🏁🏁 2 Flags  |

Scoring is calculated weekly by analyzing all athlete segment efforts logged in the database.

## 📥 Export Functionality

To download leaderboard data for a selected segment:

1. Go to /leaderboard
2. Select a segment
3. Click “⬇️ Export CSV”

## 💾 Database Structure

```sql
-- Credentials table for storing Strava authentication tokens
CREATE TABLE IF NOT EXISTS credentials (
    athlete_id INTEGER PRIMARY KEY,
    athlete_name TEXT NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at INTEGER NOT NULL
);

-- Segment efforts table for storing activity data
CREATE TABLE IF NOT EXISTS segment_efforts (
    id SERIAL PRIMARY KEY,
    athlete_name TEXT NOT NULL,
    athlete_id INTEGER NOT NULL,
    segment_id INTEGER NOT NULL,
    segment_name TEXT NOT NULL,
    activity_id BIGINT NOT NULL,
    elapsed_time INTEGER NOT NULL,
    start_date_local TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(athlete_id, segment_id, activity_id)
);

-- Athletes table for team assignment
CREATE TABLE IF NOT EXISTS athletes (
    athlete_id INTEGER PRIMARY KEY,
    athlete_name TEXT NOT NULL,
    team_name TEXT NOT NULL
);

-- Segment teams table for defining segment ownership
CREATE TABLE IF NOT EXISTS segment_teams (
    segment_id INTEGER PRIMARY KEY,
    owner_team TEXT NOT NULL,
    segment_name TEXT
);
```

## 📄 License

This project is open source and available under the MIT License.