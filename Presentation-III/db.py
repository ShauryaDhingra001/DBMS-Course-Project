"""Thin database layer: the rest of the app only calls query() / execute()."""
import datetime as dt
import sqlite3
from decimal import Decimal

import config

try:                                    # preferred MySQL driver
    import pymysql
    import pymysql.cursors
    _DRIVER = "pymysql"
    DBError = (pymysql.MySQLError,)
    IntegrityErrors = (pymysql.err.IntegrityError,)
except ImportError:
    try:                                # alternative MySQL driver
        import mysql.connector as mysql_connector
        _DRIVER = "mysql.connector"
        DBError = (mysql_connector.Error,)
        IntegrityErrors = (mysql_connector.errors.IntegrityError,)
    except ImportError:
        _DRIVER = None
        DBError, IntegrityErrors = (), ()

if config.DB_BACKEND == "sqlite":
    DBError = DBError + (sqlite3.Error,)
    IntegrityErrors = IntegrityErrors + (sqlite3.IntegrityError,)


def connect():
    if config.DB_BACKEND == "sqlite":
        conn = sqlite3.connect(config.SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    if _DRIVER == "pymysql":
        return pymysql.connect(host=config.DB_HOST, port=config.DB_PORT, user=config.DB_USER,
                               password=config.DB_PASSWORD, database=config.DB_NAME,
                               cursorclass=pymysql.cursors.DictCursor, charset="utf8mb4")
    if _DRIVER == "mysql.connector":
        return mysql_connector.connect(host=config.DB_HOST, port=config.DB_PORT, user=config.DB_USER,
                                       password=config.DB_PASSWORD, database=config.DB_NAME)
    raise RuntimeError("No MySQL driver found. Run:  pip install pymysql")


def _prep(sql):
    return sql.replace("%s", "?") if config.DB_BACKEND == "sqlite" else sql


def _args(params):
    params = tuple(params)
    if config.DB_BACKEND == "sqlite":
        return params
    return params or None               # MySQL drivers: no args -> no % formatting


def query(conn, sql, params=()):
    """Run a SELECT and return a list of dicts."""
    if _DRIVER == "mysql.connector" and config.DB_BACKEND != "sqlite":
        cur = conn.cursor(dictionary=True)
    else:
        cur = conn.cursor()
    cur.execute(_prep(sql), _args(params))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    return rows


def execute(conn, sql, params=()):
    """Run INSERT / DELETE / UPDATE, commit, return (last_insert_id, affected_rows)."""
    cur = conn.cursor()
    try:
        cur.execute(_prep(sql), _args(params))
        conn.commit()
        return cur.lastrowid, cur.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def fmt(v):
    """Make any DB value printable (MySQL returns TIME as timedelta, money as Decimal)."""
    if v is None:
        return ""
    if isinstance(v, dt.timedelta):
        s = int(v.total_seconds())
        return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    if isinstance(v, Decimal):
        return f"{v:.2f}"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)
