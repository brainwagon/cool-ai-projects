"""SQLite store: star history, LLM verdict cache, and featured repos."""

import json
import os
import sqlite3
from datetime import date, timedelta

SCHEMA = """
CREATE TABLE IF NOT EXISTS stars (
    full_name TEXT, day TEXT, stars INTEGER,
    PRIMARY KEY (full_name, day));
CREATE TABLE IF NOT EXISTS verdicts (
    full_name TEXT PRIMARY KEY, day TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS featured (
    full_name TEXT PRIMARY KEY, issue TEXT, area TEXT);
"""


class DB:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.c = sqlite3.connect(path)
        self.c.executescript(SCHEMA)

    def record_stars(self, full_name, day, stars):
        self.c.execute("INSERT OR REPLACE INTO stars VALUES (?,?,?)",
                       (full_name, day.isoformat(), stars))

    def weekly_gain(self, full_name, today, stars):
        """Stars gained since a snapshot 5-10 days ago, or None."""
        row = self.c.execute(
            "SELECT day, stars FROM stars WHERE full_name=? AND day BETWEEN ? AND ?"
            " ORDER BY day DESC LIMIT 1",
            (full_name, (today - timedelta(days=10)).isoformat(),
             (today - timedelta(days=5)).isoformat())).fetchone()
        if not row:
            return None
        days = (today - date.fromisoformat(row[0])).days
        return (stars - row[1]) * 7 / days

    def verdict(self, full_name, today, max_age_days):
        row = self.c.execute("SELECT day, data FROM verdicts WHERE full_name=?",
                             (full_name,)).fetchone()
        if row and (today - date.fromisoformat(row[0])).days <= max_age_days:
            return json.loads(row[1])
        return None

    def save_verdict(self, full_name, today, data):
        self.c.execute("INSERT OR REPLACE INTO verdicts VALUES (?,?,?)",
                       (full_name, today.isoformat(), json.dumps(data)))

    def featured_names(self):
        return {r[0] for r in self.c.execute("SELECT full_name FROM featured")}

    def mark_featured(self, full_name, issue, area):
        self.c.execute("INSERT OR REPLACE INTO featured VALUES (?,?,?)",
                       (full_name, issue, area))

    def commit(self):
        self.c.commit()
