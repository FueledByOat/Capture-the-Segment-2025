from dotenv import load_dotenv
import os

load_dotenv("secrets.env")

class Config:
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    DB_PATH = os.getenv("DB_PATH", "strava_efforts.db")