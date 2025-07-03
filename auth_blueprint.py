from flask import Blueprint, request, redirect, session, render_template_string
import requests
import os
import secrets
from database import get_db_connection 

# Create a 'Blueprint' object
auth_bp = Blueprint('auth_bp', __name__)

# Load Strava credentials from environment variables
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
# This URI must match the one set in your Strava API settings
REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI", "http://127.0.0.1:5000/callback")


@auth_bp.route('/auth-home')
def index():
    return render_template_string('''
    <h1>Strava Team Authorization</h1>
    <p>Click below to authorize your Strava account for team segment tracking:</p>
    <a href="/authorize">Authorize Strava Account</a>
    <p>This will grant the application permission to read your activity data so it can be used for scoring in the challenge. Your tokens will be stored securely in the application database.</p>
    ''')


@auth_bp.route('/authorize')
def authorize():
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    auth_url = (f"https://www.strava.com/oauth/authorize?"
                f"client_id={CLIENT_ID}&"
                f"response_type=code&"
                f"redirect_uri={REDIRECT_URI}&"
                f"scope=activity:read_all&"
                f"state={state}") # <-- CSRF protection state token 
    return redirect(auth_url)


@auth_bp.route('/callback')
def callback():
    state = request.args.get('state')
    if not state or state != session.get('oauth_state'):
        return "Invalid state parameter. Authorization failed.", 400
    
    code = request.args.get('code')
    if not code:
        return "Authorization failed; no code provided.", 400
    
    # Exchange code for tokens
    response = requests.post("https://www.strava.com/oauth/token", data={
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code'
    })
    
    if response.status_code != 200:
        return f"Token exchange failed: {response.text}", 400
    
    tokens = response.json()
    
    # Store credentials in the database
    conn = get_db_connection()
    cur = conn.cursor()
    
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
    cur.close()
    conn.close()
    
    return f"Success! {tokens['athlete']['firstname']} {tokens['athlete']['lastname']} has been authorized."