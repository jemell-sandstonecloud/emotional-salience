"""Sandstone database layer — SQLite (dev) / PostgreSQL (prod)."""

import os
import sys
import uuid
import json
import random
import sqlite3
import hashlib
import threading
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

_local = threading.local()


def get_connection():
    """Get DB connection — thread-local SQLite for dev, PostgreSQL for prod."""
    if not hasattr(_local, 'connection') or _local.connection is None:
        if config.USE_POSTGRES:
            import psycopg2
            _local.connection = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                dbname=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            _local.connection.autocommit = True
        else:
            # Read fresh from env to support test isolation
            db_path = os.environ.get('DATABASE_PATH', config.DATABASE_PATH)
            os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
            _local.connection = sqlite3.connect(db_path, check_same_thread=False)
            _local.connection.row_factory = sqlite3.Row
            _local.connection.execute("PRAGMA journal_mode=WAL")
    return _local.connection


def reset_connection():
    """Reset the connection (useful for testing)."""
    if hasattr(_local, 'connection') and _local.connection is not None:
        try:
            _local.connection.close()
        except Exception:
            pass
    _local.connection = None


def init_db():
    """Create all tables from schema."""
    conn = get_connection()
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')
    with open(schema_path, 'r') as f:
        schema = f.read()
    if config.USE_POSTGRES:
        conn.cursor().execute(schema)
    else:
        conn.executescript(schema)
    return True


# ═══════════════════════════════════════════
# Memory Node CRUD
# ═══════════════════════════════════════════

def insert_node(user_id, topic, content, scores, base_score):
    """Insert a new memory node. Returns node_id."""
    conn = get_connection()
    node_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn.execute(
        """INSERT INTO memory_nodes 
           (id, user_id, topic, content, sdv, cscv, aahs, swv, pdv, 
            base_score, current_salience, tds_score, corrected_salience, 
            processing_count, decay_rate, spike_coefficient, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (node_id, user_id, topic, content,
         scores.get('sdv', 0.0), scores.get('cscv', 0.0),
         scores.get('aahs', 0.0), scores.get('swv', 0.0), scores.get('pdv', 0.0),
         base_score, base_score, 0.0, base_score,
         0, config.BASE_DECAY_RATE, 0.0, now, now)
    )
    conn.commit()
    return node_id


def update_node(node_id, content, scores, base_score):
    """Update an existing node (for deduplication)."""
    conn = get_connection()
    now = datetime.utcnow().isoformat()
    conn.execute(
        """UPDATE memory_nodes SET 
           content=?, sdv=?, cscv=?, aahs=?, swv=?, pdv=?,
           base_score=?, current_salience=?, updated_at=?
           WHERE id=?""",
        (content, scores.get('sdv', 0.0), scores.get('cscv', 0.0),
         scores.get('aahs', 0.0), scores.get('swv', 0.0), scores.get('pdv', 0.0),
         base_score, base_score, now, node_id)
    )
    conn.commit()


def get_node_by_topic(user_id, topic):
    """Get a node by user+topic, or None."""
    conn = get_connection()
    cur = conn.execute(
        "SELECT * FROM memory_nodes WHERE user_id=? AND topic=?",
        (user_id, topic)
    )
    row = cur.fetchone()
    if row is None:
        return None
    return dict(row)


def get_nodes_by_user(user_id):
    """Get all nodes for a user, ordered by corrected_salience DESC."""
    conn = get_connection()
    cur = conn.execute(
        "SELECT * FROM memory_nodes WHERE user_id=? ORDER BY corrected_salience DESC",
        (user_id,)
    )
    return [dict(r) for r in cur.fetchall()]


def get_topic_history(topic, user_id):
    """Get prior disclosures about a topic for a user."""
    conn = get_connection()
    cur = conn.execute(
        "SELECT content, created_at FROM memory_nodes WHERE user_id=? AND topic=? ORDER BY created_at ASC",
        (user_id, topic)
    )
    return [dict(r) for r in cur.fetchall()]


def update_salience(node_id, new_salience):
    """Update current_salience for a node."""
    conn = get_connection()
    conn.execute(
        "UPDATE memory_nodes SET current_salience=?, updated_at=? WHERE id=?",
        (new_salience, datetime.utcnow().isoformat(), node_id)
    )
    conn.commit()


def update_corrected_salience(node_id, corrected):
    """Update corrected_salience for a node."""
    conn = get_connection()
    conn.execute(
        "UPDATE memory_nodes SET corrected_salience=?, updated_at=? WHERE id=?",
        (corrected, datetime.utcnow().isoformat(), node_id)
    )
    conn.commit()


def update_tds_score(node_id, tds):
    """Update TDS score for a node."""
    conn = get_connection()
    conn.execute(
        "UPDATE memory_nodes SET tds_score=?, updated_at=? WHERE id=?",
        (tds, datetime.utcnow().isoformat(), node_id)
    )
    conn.commit()


def update_decay_rate(node_id, decay_rate):
    """Update decay_rate for a node."""
    conn = get_connection()
    conn.execute(
        "UPDATE memory_nodes SET decay_rate=?, updated_at=? WHERE id=?",
        (decay_rate, datetime.utcnow().isoformat(), node_id)
    )
    conn.commit()


def mark_processed(node_id):
    """Increment processing_count and update last_processed."""
    conn = get_connection()
    now = datetime.utcnow().isoformat()
    conn.execute(
        """UPDATE memory_nodes SET 
           processing_count = processing_count + 1, 
           last_processed=?, updated_at=?
           WHERE id=?""",
        (now, now, node_id)
    )
    conn.commit()


def get_all_nodes():
    """Get all nodes (for decay engine)."""
    conn = get_connection()
    cur = conn.execute("SELECT * FROM memory_nodes")
    return [dict(r) for r in cur.fetchall()]


def get_all_users():
    """Get distinct user_ids."""
    conn = get_connection()
    cur = conn.execute("SELECT DISTINCT user_id FROM memory_nodes")
    return [row['user_id'] for row in cur.fetchall()]


def delete_node(node_id):
    """Delete a node (for archival)."""
    conn = get_connection()
    conn.execute("DELETE FROM memory_nodes WHERE id=?", (node_id,))
    conn.commit()


def insert_session(user_id):
    """Create a new session. Returns session_id."""
    conn = get_connection()
    session_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO sessions (id, user_id, started_at) VALUES (?, ?, ?)",
        (session_id, user_id, datetime.utcnow().isoformat())
    )
    conn.commit()
    return session_id


def insert_message(session_id, user_id, role, content):
    """Insert a message into a session."""
    conn = get_connection()
    msg_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO messages (id, session_id, user_id, role, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (msg_id, session_id, user_id, role, content, datetime.utcnow().isoformat())
    )
    conn.commit()
    return msg_id


# ═══════════════════════════════════════════
# Study Participants
# ═══════════════════════════════════════════

def _hash_password(password):
    """Simple SHA-256 hash for dev. Use bcrypt in prod."""
    return hashlib.sha256(password.encode()).hexdigest()


def insert_study_participant(user_id, email, display_name, sandstone_panel, password=None):
    """Insert a study participant with randomized panel assignment."""
    conn = get_connection()
    now = datetime.utcnow().isoformat()
    pw_hash = _hash_password(password) if password else ''
    conn.execute(
        """INSERT INTO study_participants 
           (user_id, email, display_name, password_hash, sandstone_panel, session_count, total_exchanges, is_admin, created_at)
           VALUES (?, ?, ?, ?, ?, 0, 0, 0, ?)""",
        (user_id, email, display_name, pw_hash, sandstone_panel, now)
    )
    conn.commit()
    return user_id


def get_study_participant(user_id):
    """Get a study participant by user_id."""
    conn = get_connection()
    cur = conn.execute("SELECT * FROM study_participants WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_study_participant_by_email(email):
    """Get a study participant by email."""
    conn = get_connection()
    cur = conn.execute("SELECT * FROM study_participants WHERE email=?", (email,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_all_study_participants():
    """Get all study participants."""
    conn = get_connection()
    cur = conn.execute("SELECT * FROM study_participants ORDER BY created_at DESC")
    return [dict(r) for r in cur.fetchall()]


def update_participant_session_count(user_id):
    """Increment session count for a participant."""
    conn = get_connection()
    conn.execute(
        "UPDATE study_participants SET session_count = session_count + 1 WHERE user_id=?",
        (user_id,)
    )
    conn.commit()


def update_participant_exchange_count(user_id):
    """Increment total exchange count for a participant."""
    conn = get_connection()
    conn.execute(
        "UPDATE study_participants SET total_exchanges = total_exchanges + 1 WHERE user_id=?",
        (user_id,)
    )
    conn.commit()


def set_participant_consent(user_id):
    """Record consent timestamp."""
    conn = get_connection()
    conn.execute(
        "UPDATE study_participants SET consent_given_at=? WHERE user_id=?",
        (datetime.utcnow().isoformat(), user_id)
    )
    conn.commit()


def set_participant_admin(user_id, is_admin=True):
    """Set admin status."""
    conn = get_connection()
    conn.execute(
        "UPDATE study_participants SET is_admin=? WHERE user_id=?",
        (1 if is_admin else 0, user_id)
    )
    conn.commit()


# ═══════════════════════════════════════════
# Study Ratings
# ═══════════════════════════════════════════

def insert_rating(user_id, session_number, exchange_number, message_text,
                  response_a_text, response_b_text,
                  response_a_attunement, response_a_contextual_accuracy, response_a_naturalness,
                  response_b_attunement, response_b_contextual_accuracy, response_b_naturalness,
                  preference, which_is_sandstone, memory_state_snapshot=None, model_id=None):
    """Insert a study rating for an exchange."""
    conn = get_connection()
    rating_id = str(uuid.uuid4())
    snapshot_json = json.dumps(memory_state_snapshot) if memory_state_snapshot else None
    conn.execute(
        """INSERT INTO study_ratings 
           (id, user_id, session_number, exchange_number, message_text,
            response_a_text, response_b_text,
            response_a_attunement, response_a_contextual_accuracy, response_a_naturalness,
            response_b_attunement, response_b_contextual_accuracy, response_b_naturalness,
            preference, which_is_sandstone, memory_state_snapshot, model_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (rating_id, user_id, session_number, exchange_number, message_text,
         response_a_text, response_b_text,
         response_a_attunement, response_a_contextual_accuracy, response_a_naturalness,
         response_b_attunement, response_b_contextual_accuracy, response_b_naturalness,
         preference, which_is_sandstone, snapshot_json, model_id,
         datetime.utcnow().isoformat())
    )
    conn.commit()
    return rating_id


def get_ratings_by_user(user_id):
    """Get all ratings for a user."""
    conn = get_connection()
    cur = conn.execute(
        "SELECT * FROM study_ratings WHERE user_id=? ORDER BY session_number, exchange_number",
        (user_id,)
    )
    return [dict(r) for r in cur.fetchall()]


def get_all_ratings():
    """Get all ratings across all users."""
    conn = get_connection()
    cur = conn.execute("SELECT * FROM study_ratings ORDER BY created_at")
    return [dict(r) for r in cur.fetchall()]


# ═══════════════════════════════════════════
# Conversation History (for stateful sessions)
# ═══════════════════════════════════════════

def insert_conversation_turn(user_id, session_number, panel, role, content, exchange_number=0):
    """Insert a conversation turn for stateful session history."""
    conn = get_connection()
    turn_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO conversation_history 
           (id, user_id, session_number, panel, role, content, exchange_number, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (turn_id, user_id, session_number, panel, role, content, exchange_number,
         datetime.utcnow().isoformat())
    )
    conn.commit()
    return turn_id


def get_conversation_history(user_id, session_number, panel):
    """Get conversation history for a user/session/panel."""
    conn = get_connection()
    cur = conn.execute(
        """SELECT * FROM conversation_history 
           WHERE user_id=? AND session_number=? AND panel=?
           ORDER BY created_at ASC""",
        (user_id, session_number, panel)
    )
    return [dict(r) for r in cur.fetchall()]


def get_latest_session_number(user_id):
    """Get the latest session number for a user, or 0 if none."""
    conn = get_connection()
    cur = conn.execute(
        "SELECT MAX(session_number) as max_session FROM conversation_history WHERE user_id=?",
        (user_id,)
    )
    row = cur.fetchone()
    if row and row['max_session'] is not None:
        return row['max_session']
    return 0
