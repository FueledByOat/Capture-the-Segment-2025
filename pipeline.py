# pipeline.py

import sqlite3
import requests
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv
import os
from utils.strava_utils import refresh_access_token

NORTH_SEGMENT_IDS = [31546864, 20462981, 29510789, 39523134, 24861084, 13197134, 8378497, 39523117]
SOUTH_SEGMENT_IDS = [1471907, 1332276, 31142862, 39499332, 22972009, 654778, 4824653, 1518106, 30471058, 26938538]
SP_SEGMENT_IDS = [39526612, 15898012, 17268802, 26192975, 26285065, 16403630, 24530544, 7080526, 22981622, 17314996]
CHALLENGE_SEGMENT_IDS = [37250565, 39505193, 37433791]
ALL_SEGMENT_IDS = NORTH_SEGMENT_IDS + SOUTH_SEGMENT_IDS + SP_SEGMENT_IDS + CHALLENGE_SEGMENT_IDS
TEST_SEGMENT = [1234]

# Segment cache to avoid repeated API calls
segment_cache = {}

def get_segment_info(segment_id, headers):
    """Cache segment metadata to avoid repeated lookups"""
    if segment_id not in segment_cache:
        response = requests.get(f"https://www.strava.com/api/v3/segments/{segment_id}", headers=headers)
        time.sleep(0.1)  # Rate limiting
        if response.status_code == 200:
            segment_cache[segment_id] = response.json()
        else:
            segment_cache[segment_id] = None
    return segment_cache[segment_id]

def fetch_and_store_efforts(token, athlete_id, athlete_name, cur, segment_ids):
    headers = {'Authorization': f'Bearer {token}'}
    after = int((datetime.now() - timedelta(days=30)).timestamp())
    
    # More efficient: get activities with segment efforts included
    params = {
        "after": after,
        "per_page": 50,
        "page": 1,
        "include_all_efforts": True  # Include segment efforts in response
    }
    
    batch_data = []  # Collect data for batch insert
    
    activities = requests.get("https://www.strava.com/api/v3/athlete/activities", 
                            headers=headers, params=params).json()
    time.sleep(0.1)  # Rate limiting after API call
    
    for activity in activities:
        # Skip detailed activity fetch if segment_efforts already included
        if "segment_efforts" in activity and activity["segment_efforts"]:
            efforts = activity["segment_efforts"]
        else:
            # Fallback to detailed fetch if needed
            details = requests.get(f"https://www.strava.com/api/v3/activities/{activity['id']}", 
                                 headers=headers).json()
            time.sleep(0.1)  # Rate limiting
            efforts = details.get("segment_efforts", [])
        
        for effort in efforts:
            sid = effort["segment"]["id"]
            if sid in segment_ids:
                # Collect data for batch insert instead of individual inserts
                batch_data.append((
                    athlete_name, athlete_id, sid, effort["segment"]["name"], 
                    activity["id"], effort["elapsed_time"], effort["start_date_local"]
                ))
    
    # Batch database operations in single transaction
    if batch_data:
        cur.executemany("""
            INSERT OR IGNORE INTO segment_efforts
            (athlete_name, athlete_id, segment_id, segment_name, activity_id, elapsed_time, start_date_local)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, batch_data)

def update_tokens_and_fetch_activities():
    load_dotenv("secrets.env")
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    
    # Define your 33 segments here
    SEGMENT_IDS = [1234, 5678, 9012]  # Replace with your actual segment IDs
    
    conn = sqlite3.connect("strava_efforts.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Begin transaction for all operations
    conn.execute("BEGIN")
    
    try:
        cur.execute("SELECT * FROM credentials")
        for user in cur.fetchall():
            if int(time.time()) >= user["expires_at"]:
                print(f"Refreshing token for {user['athlete_name']}")
                tokens = refresh_access_token(client_id, client_secret, user["refresh_token"])
                cur.execute("""
                    UPDATE credentials SET access_token=?, refresh_token=?, expires_at=?
                    WHERE athlete_id=?
                """, (tokens['access_token'], tokens['refresh_token'], 
                     tokens['expires_at'], user["athlete_id"]))
                access_token = tokens["access_token"]
            else:
                access_token = user["access_token"]
            
            fetch_and_store_efforts(access_token, user["athlete_id"], 
                                  user["athlete_name"], cur, SEGMENT_IDS)
            
            # Rate limiting between users
            time.sleep(0.2)
        
        conn.commit()  # Commit all changes at once
        
    except Exception as e:
        conn.rollback()  # Rollback on error
        print(f"Error during update: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    update_tokens_and_fetch_activities()