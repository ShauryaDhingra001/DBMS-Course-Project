"""Database settings. Edit these (or set environment variables) to match your MySQL."""
import os

DB_BACKEND = os.getenv("DB_BACKEND", "mysql")        # "mysql" (real project) or "sqlite" (demo fallback)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Bruno@1/")
DB_NAME = os.getenv("DB_NAME", "laboratory_management")
SQLITE_PATH = os.getenv("SQLITE_PATH", "demo.db")
SECRET_KEY = os.getenv("SECRET_KEY", "lab-equipment-dbms-2026")
