
import sqlite3
import json
from datetime import datetime, timezone


class SQLiteDatabase:

    def __init__(self, path="expert_memory.db"):
        self.conn = sqlite3.connect(path)
        self.create_tables()


    def create_tables(self):

        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            version INTEGER,
            pattern_hash TEXT,
            regime TEXT,
            timeframe TEXT,
            state TEXT,
            confidence REAL,
            evidence TEXT,
            created_at TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS decision_traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id TEXT,
            pattern TEXT,
            confidence REAL,
            risk_state TEXT,
            stage TEXT,
            trace TEXT,
            created_at TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern TEXT,
            prediction TEXT,
            actual TEXT,
            result TEXT,
            reward REAL,
            created_at TEXT
        )
        """)

        self.conn.commit()


class KnowledgeRepository:

    def __init__(self, db):
        self.db = db


    def save(self, knowledge):

        self.db.conn.execute(
            """
            INSERT INTO knowledge_memory
            VALUES(
            NULL,?,?,?,?,?,?,?,?,?
            )
            """,
            (
                knowledge.name,
                knowledge.version,
                knowledge.pattern_hash,
                knowledge.regime,
                knowledge.timeframe_signature,
                knowledge.state,
                knowledge.confidence,
                json.dumps(knowledge.evidence),
                datetime.now(timezone.utc).isoformat()
            )
        )

        self.db.conn.commit()


class DecisionRepository:

    def __init__(self, db):
        self.db = db


    def save(self, trace):

        self.db.conn.execute(
            """
            INSERT INTO decision_traces
            VALUES(
            NULL,?,?,?,?,?,?,?
            )
            """,
            (
                trace.decision_id,
                trace.pattern,
                trace.confidence,
                trace.risk_state,
                trace.stage,
                json.dumps(trace.trace),
                trace.timestamp
            )
        )

        self.db.conn.commit()


class FeedbackRepository:

    def __init__(self, db):
        self.db = db


    def save(
        self,
        pattern,
        prediction,
        actual,
        result,
        reward
    ):

        self.db.conn.execute(
            """
            INSERT INTO feedback_history
            VALUES(
            NULL,?,?,?,?,?,?
            )
            """,
            (
                pattern,
                prediction,
                actual,
                result,
                reward,
                datetime.now(timezone.utc).isoformat()
            )
        )

        self.db.conn.commit()
