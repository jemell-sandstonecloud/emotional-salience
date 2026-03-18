"""Shared test utilities for PostgreSQL test database."""

import os
import sys
import unittest
import testing.postgresql

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Spin up a throwaway Postgres instance for the test run
_postgresql = testing.postgresql.Postgresql()
_dsn = _postgresql.dsn()

# Point all DB env vars at the throwaway instance
os.environ['DB_HOST'] = _dsn['host']
os.environ['DB_PORT'] = str(_dsn['port'])
os.environ['DB_NAME'] = _dsn['database']
os.environ['DB_USER'] = _dsn.get('user', 'postgres')
os.environ['DB_PASSWORD'] = ''

import config
from db.database import get_connection, reset_connection, init_db


class SandstoneTestCase(unittest.TestCase):
    """Base test case that sets up and tears down a clean test database."""

    @classmethod
    def setUpClass(cls):
        """Create tables in test database."""
        reset_connection()
        init_db()

    def setUp(self):
        """Clear all tables before each test."""
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM conversation_history")
            cur.execute("DELETE FROM study_ratings")
            cur.execute("DELETE FROM messages")
            cur.execute("DELETE FROM sessions")
            cur.execute("DELETE FROM memory_nodes")
            cur.execute("DELETE FROM study_participants")

    @classmethod
    def tearDownClass(cls):
        """Close connection."""
        reset_connection()
