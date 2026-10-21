"""Database connection. Every query in the app opens one with get_connection() and closes it afterwards."""

import os

import psycopg2


def get_connection():
    """Open a database connection from DATABASE_URL (falls back to a local 'bmac' database)."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)
    return psycopg2.connect(dbname="hazbat", user="ed_hzj", host="localhost")
