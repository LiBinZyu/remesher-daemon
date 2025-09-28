"""
SQLite database interface for task management.
Defines the 'tasks' table and core functions: add_task, get_next_task, update_status.
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = None

def init_db(db_path):
    global DB_PATH
    DB_PATH = db_path
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            uuid TEXT PRIMARY KEY,
            source_path TEXT,
            status TEXT,
            created_at DATETIME,
            log_message TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_task(path):
    import uuid
    if DB_PATH is None:
        raise RuntimeError("Database not initialized. Call init_db(db_path) first.")
    task_uuid = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO tasks (uuid, source_path, status, created_at) VALUES (?, ?, ?, ?)",
        (task_uuid, path, "PENDING", datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return task_uuid

def get_next_task():
    if DB_PATH is None:
        raise RuntimeError("Database not initialized. Call init_db(db_path) first.")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT uuid, source_path, status, created_at, log_message FROM tasks WHERE status = 'PENDING' ORDER BY created_at LIMIT 1"
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "uuid": row[0],
            "source_path": row[1],
            "status": row[2],
            "created_at": row[3],
            "log_message": row[4]
        }
    return None

def update_status(uuid, status, message=None):
    if DB_PATH is None:
        raise RuntimeError("Database not initialized. Call init_db(db_path) first.")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if message is not None:
        c.execute(
            "UPDATE tasks SET status = ?, log_message = ? WHERE uuid = ?",
            (status, message, uuid)
        )
    else:
        c.execute(
            "UPDATE tasks SET status = ? WHERE uuid = ?",
            (status, uuid)
        )
    conn.commit()
    conn.close()

def mark_processing_as_failed():
    """
    将所有PROCESSING状态的任务重置为FAILED，返回受影响的任务数。
    """
    if DB_PATH is None:
        raise RuntimeError("Database not initialized. Call init_db(db_path) first.")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE tasks SET status = 'FAILED', log_message = 'Reset by daemon startup' WHERE status = 'PROCESSING'"
    )
    count = c.rowcount
    conn.commit()
    conn.close()
    return count
