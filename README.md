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
- SQLite
- HTML/CSS (templated with Jinja2)
- Strava API (OAuth2 access and activity data)
- CSV and in-browser rendering

---

## 🗂 Project Structure
```bash
strava-segment-tracker/
│
├── app.py # Main Flask app with leaderboard + scoring logic
├── strava_efforts.db # SQLite DB with segments, efforts, and tokens
├── templates/
│ ├── base.html
│ ├── home.html
│ ├── leaderboard.html
│ └── scoreboard.html
├── static/
│ └── style.css # Custom styles using defined color palette
├── utils/
│ └── strava_utils.py # (optional) Utility functions for token refresh, API calls
├── config.py # Stores environment variable references
├── secrets.env # Environment secrets like STRAVA client ID/secret
└── README.md
```

## ⚙️ Setup Instructions

### 1. Clone and install dependencies

```bash
git clone https://github.com/yourusername/strava-segment-tracker.git
cd strava-segment-tracker
pip install -r requirements.txt
```

2. Set up environment

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

## 🧪 Testing with Sample Data

You can manually populate ```strava_efforts.db``` using the ```sqlite3``` CLI or with Python scripts using ```INSERT INTO segment_efforts (...) VALUES (...)```.

Each effort should include:

- athlete_name
- segment_id
- segment_name
- elapsed_time
- team_name

## 📄 License

This project is open source and available under the MIT License.