# strava_utils.py

import requests
import sqlite3
import time

def refresh_access_token(client_id, client_secret, refresh_token):
    response = requests.post("https://www.strava.com/oauth/token", data={
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    })
    response.raise_for_status()
    tokens = response.json()
    return tokens
