# self_service_auth_app.py
"""
Self-service Strava authorization web app - PostgreSQL Version
Teammates can authorize themselves without sharing tokens
"""
from flask import Flask, request, redirect, session, render_template_string
import requests
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

load_dotenv("secrets.env")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = "http://localhost:5000/callback"

def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", 5432),
        sslmode='require'
    )

@app.route('/')
def index():
    return render_template_string('''
    <h1>Strava Team Authorization</h1>
    <p>Click below to authorize your Strava account for team segment tracking:</p>
    <a href="/authorize">Authorize Strava Account</a>
    <p>For transparency, the scope being requested is activity:read_all which grants an application permission to access an athlete's activity data, including activities with visibility set to "Only You".</p>
    <p> Here's what that means:</p>
    <li>Expanded Access: It allows an application to read activity data for activities that are visible to "Everyone", "Followers", and those marked as "Only You", which are typically private.</li>
    <p> Why is this being requested?</p>
    <p> This access allows us programmatically pull data for all CTS users for scoring. The access token provided will be stored securely in a database in Microsoft's Azure platform. Once CTS is over, that resource will be destroyed, and access will no longer be possible. To allay any further concern the access the token provided expires shortly after it is not refreshed.</p>
    ''')

@app.route('/authorize')
def authorize():
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    auth_url = f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope=activity:read_all"
    return redirect(auth_url)

@app.route('/callback')
def callback():
    state = request.args.get('state')
    if not state or state != session.get('oauth_state'):
        return "Invalid state parameter. Authorization failed.", 400
    
    code = request.args.get('code')
    if not code:
        return "Authorization failed", 400
   
    # Exchange code for tokens
    response = requests.post("https://www.strava.com/oauth/token", data={
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code'
    })
   
    if response.status_code != 200:
        return "Token exchange failed", 400
   
    tokens = response.json()
   
    # Store in database
    conn = get_db_connection()
    cur = conn.cursor()
   
    # Create table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS credentials (
            athlete_id INTEGER PRIMARY KEY,
            athlete_name TEXT,
            access_token TEXT,
            refresh_token TEXT,
            expires_at INTEGER
        )
    """)
   
    # Insert credentials using PostgreSQL upsert
    cur.execute("""
        INSERT INTO credentials
        (athlete_id, athlete_name, access_token, refresh_token, expires_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (athlete_id) DO UPDATE SET
            athlete_name = EXCLUDED.athlete_name,
            access_token = EXCLUDED.access_token,
            refresh_token = EXCLUDED.refresh_token,
            expires_at = EXCLUDED.expires_at
    """, (
        tokens['athlete']['id'],
        f"{tokens['athlete']['firstname']} {tokens['athlete']['lastname']}",
        tokens['access_token'],
        tokens['refresh_token'],
        tokens['expires_at']
    ))
   
    conn.commit()
    conn.close()
   
    return f"Success! {tokens['athlete']['firstname']} {tokens['athlete']['lastname']} has been authorized."

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5001)