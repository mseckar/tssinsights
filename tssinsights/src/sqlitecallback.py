import sqlite3
from src.policytree import PolicyTree

class SqliteCallback():
    """SQLite helper class"""
    def __init__(self, name: str) -> None:
        self.conn = sqlite3.connect(name)
        self.cursor = self.conn.cursor()

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS PolicyTrees (
            id INTEGER PRIMARY KEY,
            policy TEXT,
            miniscript TEXT,
            anonymized_miniscript TEXT
        )
        ''')
        self.conn.commit()

    def store(self, tree: PolicyTree) -> None:
        try:
            self.cursor.execute('''
            INSERT OR IGNORE INTO PolicyTrees (policy, miniscript) VALUES (?, ?)
            ''', (repr(tree), tree.miniscript))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Database error: {e}")

    def close(self) -> None:
        self.conn.close()