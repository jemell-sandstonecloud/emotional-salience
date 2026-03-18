"""Sandstone database layer — PostgreSQL via psycopg2."""

import os
import sys
import uuid
import json
import random
import hashlib
import threading
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

_local = threading.local()


def get_connection():
    """Get thread-local PostgreSQL connection."""
    if not hasattr(_local, 'connection') or _local.connection is None or _local.connection.closed:
        _local.connection = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
        )
        _local.connection.autocommit = True
    return _local.connection


def reset_connection():
    """Reset the connection (useful for testing)."""
    if hasattr(_local, 'connection') and _local.connection is not None:
        try:
            _local.connection.close()
        except Exception:
            pass
    _local.connection = None


def _query(sql, params=None, fetch=False, fetchone=False):
    """Execute a query with RealDictCursor. Returns rows for fetch queries."""
    conn = get_connection()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        if fetchone:
            row = cur.fetchone()
            return dict(row) if row else None
        if fetch:
            return [dict(r) for r in cur.fetchall()]
    return None


def _execute(sql, params=None):
    """Execute a write query (INSERT/UPDATE/DELETE)."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(sql, params)


def init_db():
    """Create all tables from schema."""
    conn = get_connection()
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')
    with open(schema_path, 'r') as f:
        schema = f.read()
    with conn.cursor() as cur:
        cur.execute(schema)
    return True


# ==============================
# Memory Node CRUD
# ==============================

def insert_node(user_id, topic, content, scores, base_score):
    """Insert a new memory node. Returns node_id."""
    node_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    _execute(
        """INSERT INTO memory_nodes
           (id, user_id, topic, content, sdv, cscv, lcs, swv, pdv,
            base_score, current_salience, lds_score, corrected_salience,
            processing_count, decay_rate, spike_coefficient, created_at, updated_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (node_id, user_id, topic, content,
         scores.get('sdv', 0.0), scores.get('cscv', 0.0),
         scores.get('lcs', 0.0), scores.get('swv', 0.0), scores.get('pdv', 0.0),
         base_score, base_score, 0.0, base_score,
         0, config.BASE_DECAY_RATE, 0.0, now, now)
    )
    return node_id


def update_node(node_id, content, scores, base_score):
    """Update an existing node (for deduplication)."""
    now = datetime.utcnow().isoformat()
    _execute(
        """UPDATE memory_nodes SET
           content=%s, sdv=%s, cscv=%s, lcs=%s, swv=%s, pdv=%s,
           base_score=%s, current_salience=%s, updated_at=%s
           WHERE id=%s""",
        (content, scores.get('sdv', 0.0), scores.get('cscv', 0.0),
         scores.get('lcs', 0.0), scores.get('swv', 0.0), scores.get('pdv', 0.0),
         base_score, base_score, now, node_id)
    )


def get_node_by_topic(user_id, topic):
    """Get a node by user+topic, or None."""
    return _query(
        "SELECT * FROM memory_nodes WHERE user_id=%s AND topic=%s",
        (user_id, topic), fetchone=True
    )


def get_nodes_by_user(user_id):
    """Get all nodes for a user, ordered by corrected_salience DESC."""
    return _query(
        "SELECT * FROM memory_nodes WHERE user_id=%s ORDER BY corrected_salience DESC",
        (user_id,), fetch=True
    )


def get_topic_history(topic, user_id):
    """Get prior disclosures about a topic for a user."""
    return _query(
        "SELECT content, created_at FROM memory_nodes WHERE user_id=%s AND topic=%s ORDER BY created_at ASC",
        (user_id, topic), fetch=True
    )


def update_salience(node_id, new_salience):
    """Update current_salience for a node."""
    _execute(
        "UPDATE memory_nodes SET current_salience=%s, updated_at=%s WHERE id=%s",
        (new_salience, datetime.utcnow().isoformat(), node_id)
    )


def update_corrected_salience(node_id, corrected):
    """Update corrected_salience for a node."""
    _execute(
        "UPDATE memory_nodes SET corrected_salience=%s, updated_at=%s WHERE id=%s",
        (corrected, datetime.utcnow().isoformat(), node_id)
    )


def update_lds_score(node_id, tds):
    """Update TDS score for a node."""
    _execute(
        "UPDATE memory_nodes SET lds_score=%s, updated_at=%s WHERE id=%s",
        (tds, datetime.utcnow().isoformat(), node_id)
    )


def update_decay_rate(node_id, decay_rate):
    """Update decay_rate for a node."""
    _execute(
        "UPDATE memory_nodes SET decay_rate=%s, updated_at=%s WHERE id=%s",
        (decay_rate, datetime.utcnow().isoformat(), node_id)
    )


def mark_processed(node_id):
    """Increment processing_count and update last_processed."""
    now = datetime.utcnow().isoformat()
    _execute(
        """UPDATE memory_nodes SET
           processing_count = processing_count + 1,
           last_processed=%s, updated_at=%s
           WHERE id=%s""",
        (now, now, node_id)
    )


def get_all_nodes():
    """Get all nodes (for decay engine)."""
    return _query("SELECT * FROM memory_nodes", fetch=True)


def get_all_users():
    """Get distinct user_ids."""
    rows = _query("SELECT DISTINCT user_id FROM memory_nodes", fetch=True)
    return [row['user_id'] for row in rows]


def delete_node(node_id):
    """Delete a node (for archival)."""
    _execute("DELETE FROM memory_nodes WHERE id=%s", (node_id,))


def insert_session(user_id):
    """Create a new session. Returns session_id."""
    session_id = str(uuid.uuid4())
    _execute(
        "INSERT INTO sessions (id, user_id, started_at) VALUES (%s, %s, %s)",
        (session_id, user_id, datetime.utcnow().isoformat())
    )
    return session_id


def insert_message(session_id, user_id, role, content):
    """Insert a message into a session."""
    msg_id = str(uuid.uuid4())
    _execute(
        "INSERT INTO messages (id, session_id, user_id, role, content, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
        (msg_id, session_id, user_id, role, content, datetime.utcnow().isoformat())
    )
    return msg_id


# ==============================
# Study Participants
# ==============================

def _hash_password(password):
    """Hash password with bcrypt. Falls back to SHA-256 if bcrypt unavailable."""
    try:
        import bcrypt
        if isinstance(password, str):
            password = password.encode('utf-8')
        return bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')
    except ImportError:
        return hashlib.sha256(password.encode()).hexdigest()


def _verify_password(password, stored_hash):
    """Verify password against stored hash. Supports both bcrypt and SHA-256."""
    try:
        import bcrypt
        if isinstance(password, str):
            password = password.encode('utf-8')
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode('utf-8')
        return bcrypt.checkpw(password, stored_hash)
    except (ImportError, ValueError):
        # Fallback: SHA-256 comparison for legacy hashes
        if isinstance(password, bytes):
            password = password.decode('utf-8')
        return hashlib.sha256(password.encode()).hexdigest() == stored_hash


def insert_study_participant(user_id, email, display_name, sandstone_panel, password=None):
    """Insert a study participant."""
    now = datetime.utcnow().isoformat()
    pw_hash = _hash_password(password) if password else ''
    _execute(
        """INSERT INTO study_participants
           (user_id, email, display_name, password_hash, sandstone_panel,
            session_count, total_exchanges, is_admin, created_at)
           VALUES (%s,%s,%s,%s,%s, 0, 0, FALSE, %s)""",
        (user_id, email, display_name, pw_hash, sandstone_panel, now)
    )
    return user_id


def get_study_participant(user_id):
    """Get a study participant by user_id."""
    return _query(
        "SELECT * FROM study_participants WHERE user_id=%s",
        (user_id,), fetchone=True
    )


def get_study_participant_by_email(email):
    """Get a study participant by email."""
    return _query(
        "SELECT * FROM study_participants WHERE email=%s",
        (email,), fetchone=True
    )


def get_all_study_participants():
    """Get all study participants."""
    return _query(
        "SELECT * FROM study_participants ORDER BY created_at DESC",
        fetch=True
    )


def update_participant_session_count(user_id):
    """Increment session count for a participant."""
    _execute(
        "UPDATE study_participants SET session_count = session_count + 1 WHERE user_id=%s",
        (user_id,)
    )


def update_participant_exchange_count(user_id):
    """Increment total exchange count for a participant."""
    _execute(
        "UPDATE study_participants SET total_exchanges = total_exchanges + 1 WHERE user_id=%s",
        (user_id,)
    )


def set_participant_consent(user_id):
    """Record consent timestamp."""
    _execute(
        "UPDATE study_participants SET consent_given_at=%s WHERE user_id=%s",
        (datetime.utcnow().isoformat(), user_id)
    )


def set_participant_admin(user_id, is_admin=True):
    """Set admin status."""
    _execute(
        "UPDATE study_participants SET is_admin=%s WHERE user_id=%s",
        (is_admin, user_id)
    )


# ==============================
# Study Ratings
# ==============================

def insert_rating(user_id, session_number, exchange_number, message_text,
                  response_a_text, response_b_text,
                  response_a_attunement, response_a_contextual_accuracy, response_a_naturalness,
                  response_b_attunement, response_b_contextual_accuracy, response_b_naturalness,
                  preference, which_is_sandstone, memory_state_snapshot=None, model_id=None):
    """Insert a study rating for an exchange."""
    rating_id = str(uuid.uuid4())
    snapshot_json = json.dumps(memory_state_snapshot) if memory_state_snapshot else None
    _execute(
        """INSERT INTO study_ratings
           (id, user_id, session_number, exchange_number, message_text,
            response_a_text, response_b_text,
            response_a_attunement, response_a_contextual_accuracy, response_a_naturalness,
            response_b_attunement, response_b_contextual_accuracy, response_b_naturalness,
            preference, which_is_sandstone, memory_state_snapshot, model_id, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (rating_id, user_id, session_number, exchange_number, message_text,
         response_a_text, response_b_text,
         response_a_attunement, response_a_contextual_accuracy, response_a_naturalness,
         response_b_attunement, response_b_contextual_accuracy, response_b_naturalness,
         preference, which_is_sandstone, snapshot_json, model_id,
         datetime.utcnow().isoformat())
    )
    return rating_id


def get_ratings_by_user(user_id):
    """Get all ratings for a user."""
    return _query(
        "SELECT * FROM study_ratings WHERE user_id=%s ORDER BY session_number, exchange_number",
        (user_id,), fetch=True
    )


def get_all_ratings():
    """Get all ratings across all users."""
    return _query("SELECT * FROM study_ratings ORDER BY created_at", fetch=True)


# ==============================
# Conversation History
# ==============================

def insert_conversation_turn(user_id, session_number, panel, role, content, exchange_number=0):
    """Insert a conversation turn for stateful session history."""
    turn_id = str(uuid.uuid4())
    _execute(
        """INSERT INTO conversation_history
           (id, user_id, session_number, panel, role, content, exchange_number, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (turn_id, user_id, session_number, panel, role, content, exchange_number,
         datetime.utcnow().isoformat())
    )
    return turn_id


def get_conversation_history(user_id, session_number, panel):
    """Get conversation history for a user/session/panel."""
    return _query(
        """SELECT * FROM conversation_history
           WHERE user_id=%s AND session_number=%s AND panel=%s
           ORDER BY created_at ASC""",
        (user_id, session_number, panel), fetch=True
    )


def get_latest_session_number(user_id):
    """Get the latest session number for a user, or 0 if none."""
    row = _query(
        "SELECT MAX(session_number) as max_session FROM conversation_history WHERE user_id=%s",
        (user_id,), fetchone=True
    )
    if row and row['max_session'] is not None:
        return row['max_session']
    return 0
