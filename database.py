import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

def get_db_connection():
    """Gets a PostgreSQL database connection."""
    load_dotenv() # Looks for .env file in the root
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", 5432),
        sslmode='require'
    )