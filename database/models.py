"""SQL-схемы таблиц базы данных."""

CREATE_WORKING_DAYS_TABLE = """
CREATE TABLE IF NOT EXISTS working_days (
    date TEXT PRIMARY KEY,
    is_closed INTEGER DEFAULT 0
);
"""

CREATE_SLOTS_TABLE = """
CREATE TABLE IF NOT EXISTS slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    is_booked INTEGER DEFAULT 0,
    UNIQUE(date, time)
);
"""

CREATE_APPOINTMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    user_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    slot_id INTEGER NOT NULL,
    is_active INTEGER DEFAULT 1,
    reminder_sent INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (slot_id) REFERENCES slots (id)
);
"""
