"""Shared test utilities for PostgreSQL test database."""

import os
import sys
import unittest

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test database config - uses a local test PostgreSQL database
# Override these env vars for CI or custom test DB
os.environ.setdefault('DB_HOST', os.getenv('TEST_DB_HOST', 'localhost'))
os.environ.setdefault('DB_PORT', os.getenv('TEST_DB_PORT', '5432'))
os.environ.setdefault('DB_NAME', os.getenv('TEST_DB_NAME', 'sandstone_test'))
os.environ.setdefault('DB_USER', os.getenv('TEST_DB_USER', 'sandstone_admin'))
os.environ.setdefault('DB_PASSWORD', os.getenv('TEST_DB_PASSWORD', ''))

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
