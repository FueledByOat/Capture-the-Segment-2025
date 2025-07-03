#pipeline_logic.py
# This file contains the logic from your original pipeline.py
import logging
import requests
import time
import os
from datetime import datetime
from dotenv import load_dotenv

import psycopg2
import psycopg2.extras

# You must deploy database.py and strava_utils.py with the function
from database import get_db_connection
from utils.strava_utils import refresh_access_token

logger = logging.getLogger(__name__)

# Segment definitions
NORTH_SEGMENT_IDS = [31546864, 20462981, 29510789, 39523134, 24861084, 13197134, 8378497, 39523117]
SOUTH_SEGMENT_IDS = [1471907, 1332276, 31142862, 39499332, 22972009, 654778, 4824653, 1518106, 30471058, 26938538]
STP_SEGMENT_IDS = [39526612, 15898012, 17268802, 26192975, 26285065, 16403630, 24530544, 7080526, 22981622, 17314996]

# Challenge segments with time windows
CHALLENGE_SEGMENT_ONE = [37250565]  # valid from 1751864400 to 1751950800
CHALLENGE_SEGMENT_TWO = [39505193]  # valid from 1751950800 to 1752037200
CHALLENGE_SEGMENT_THREE = [37433791] # valid from 1752037200 to 1752123600

ALL_SEGMENT_IDS = NORTH_SEGMENT_IDS + SOUTH_SEGMENT_IDS + STP_SEGMENT_IDS + CHALLENGE_SEGMENT_ONE + CHALLENGE_SEGMENT_TWO + CHALLENGE_SEGMENT_THREE
TEST_SEGMENT = [1332276]

def get_valid_challenge_segments(timestamp):
    """
    Returns challenge segments valid for the given timestamp.
    
    Args:
        timestamp (int): Unix timestamp to check
        
    Returns:
        list: Valid challenge segment IDs
    """
    valid_segments = []
    
    if 1751864400 <= timestamp < 1751950800:
        valid_segments.extend(CHALLENGE_SEGMENT_ONE)
    if 1751950800 <= timestamp < 1752037200:
        valid_segments.extend(CHALLENGE_SEGMENT_TWO)
    if 1752037200 <= timestamp < 1752123600:
        valid_segments.extend(CHALLENGE_SEGMENT_THREE)
        
    return valid_segments

# Segment cache to avoid repeated API calls
segment_cache = {}

def fetch_and_store_efforts(token, athlete_id, athlete_name, cur, segment_ids):
    """
    Fetch segment efforts for a user and store in database.
    
    Args:
        token (str): Strava access token
        athlete_id (int): Strava athlete ID
        athlete_name (str): Athlete display name
        cur: Database cursor
        segment_ids (list): List of segment IDs to track
    """
    headers = {'Authorization': f'Bearer {token}'}
    after = 1751864400  # Start of tracking period
    after = 1751418832 # Use this for testing 
    before = 1752454800  # End of tracking period
    
    params = {
        "before": before,
        "after": after,
        "per_page": 50,
        "page": 1,
        "include_all_efforts": True
    }
    
    batch_data = []
    
    try:
        # Get activities with pagination support
        page = 1
        while True:
            params["page"] = page
            
            response = requests.get("https://www.strava.com/api/v3/athlete/activities", 
                                  headers=headers, params=params, timeout=10)
            time.sleep(0.1)  # Rate limiting
            
            if response.status_code == 429:
                logger.warning("Rate limit hit, waiting 60 seconds...")
                time.sleep(60)
                continue
                
            response.raise_for_status()
            activities = response.json()
            
            if not activities:
                break
                
            logger.info(f"Processing page {page} ({len(activities)} activities) for {athlete_name}")
            
            for activity in activities:
                activity_timestamp = int(datetime.fromisoformat(activity["start_date_local"].replace('Z', '+00:00')).timestamp())
                
                # Get valid challenge segments for this activity's timestamp
                valid_challenge_segments = get_valid_challenge_segments(activity_timestamp)
                valid_segments = set(segment_ids + valid_challenge_segments)
                
                # Process segment efforts
                efforts = []
                if "segment_efforts" in activity and activity["segment_efforts"]:
                    efforts = activity["segment_efforts"]
                else:
                    # Fallback to detailed fetch
                    try:
                        details = requests.get(f"https://www.strava.com/api/v3/activities/{activity['id']}", 
                                             headers=headers, timeout=10).json()
                        time.sleep(0.1)
                        efforts = details.get("segment_efforts", [])
                    except requests.RequestException as e:
                        logger.error(f"Failed to fetch activity {activity['id']}: {e}")
                        continue
                
                for effort in efforts:
                    sid = effort["segment"]["id"]
                    if sid in valid_segments:
                        batch_data.append((
                            athlete_name, athlete_id, sid, effort["segment"]["name"], 
                            activity["id"], effort["elapsed_time"], effort["start_date_local"]
                        ))
            
            page += 1
            
    except requests.RequestException as e:
        logger.error(f"Error fetching activities for {athlete_name}: {e}")
        return
    
    # Batch insert collected data
    if batch_data:
        try:
            cur.executemany("""
                INSERT INTO segment_efforts
                (athlete_name, athlete_id, segment_id, segment_name, activity_id, elapsed_time, start_date_local)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (athlete_id, segment_id, activity_id) DO NOTHING
            """, batch_data)
            logger.info(f"Inserted {len(batch_data)} efforts for {athlete_name}")
        except psycopg2.Error as e:
            logger.error(f"Database error inserting efforts: {e}")
            raise

def update_tokens_and_fetch_activities():
    """Main function to update tokens and fetch segment efforts for all users."""
    logger = logging.getLogger(__name__)
    load_dotenv()
    
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    
    if not client_id or not client_secret:
        logger.error("Missing CLIENT_ID or CLIENT_SECRET in environment")
        return

     
    # Use TEST_SEGMENT for testing, ALL_SEGMENT_IDS for production
    SEGMENT_IDS = TEST_SEGMENT
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        cur.execute("SELECT * FROM credentials")
        users = cur.fetchall()
        
        if not users:
            logger.warning("No users found in credentials table")
            return
            
        logger.info(f"Processing {len(users)} users")
        
        for user in users:
            logger.info(f"Processing user: {user['athlete_name']}")
            
            # Check if token needs refresh
            if int(time.time()) >= user["expires_at"]:
                logger.info(f"Refreshing token for {user['athlete_name']}")
                try:
                    tokens = refresh_access_token(client_id, client_secret, user["refresh_token"])
                    cur.execute("""
                        UPDATE credentials SET access_token=%s, refresh_token=%s, expires_at=%s
                        WHERE athlete_id=%s
                    """, (tokens['access_token'], tokens['refresh_token'], 
                         tokens['expires_at'], user["athlete_id"]))
                    access_token = tokens["access_token"]
                    logger.info(f"Token refreshed for {user['athlete_name']}")
                except Exception as e:
                    logger.error(f"Failed to refresh token for {user['athlete_name']}: {e}")
                    continue
            else:
                access_token = user["access_token"]
            
            # Fetch and store efforts
            fetch_and_store_efforts(access_token, user["athlete_id"], 
                                  user["athlete_name"], cur, SEGMENT_IDS)
            
            # Rate limiting between users
            time.sleep(0.2)
        
        conn.commit()
        logger.info("All users processed successfully")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error during update: {e}")
        raise
    finally:
        conn.close()
    logger.info("Pipeline execution finished.")