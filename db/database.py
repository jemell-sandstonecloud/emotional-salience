"""Sandstone database layer — SQLite (dev) / PostgreSQL (prod)."""

import os
import sys
import uuid
import json
import hashlib
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

_local = threading.local()


def get_connection():
    """Get DB connection — thread-local SQLite for dev, PostgreSQL for prod."""
    if not hasattr(_local, 'connection') or _local.connection is None:
        if config.USE_POSTGRES:
            import psycopg2
            import psycopg2.extras
            _local.connection = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                dbname=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            _local.connection.autocommit = True
        else:
            import sqlite3
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


def _cursor(conn):
    """Return a RealDictCursor for postgres, or plain cursor for sqlite."""
    if config.USE_POSTGRES:
        import psycopg2.extras
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        return conn.cursor()


def _ph():
    """Return the correct placeholder string for the current DB."""
    return '%s' if config.USE_POSTGRES else '?'


def _exec(conn, sql, params=()):
    """Execute a statement, replacing ? with %s for postgres."""
    if config.USE_POSTGRES:
        sql = sql.replace('?', '%s')
    cur = _cursor(conn)
    cur.execute(sql, params)
    return cur


def _row(cur):
    """Fetch one row as a dict."""
    row = cur.fetchone()
    if row is None:
        return None
    return dict(row)


def _rows(cur):
    """Fetch all rows as list of dicts."""
    return [dict(r) for r in cur.fetchall()]


def _commit(conn):
    """Commit only for SQLite (postgres uses autocommit)."""
    if not config.USE_POSTGRES:
        conn.commit()


def init_db():
    """Create all tables from schema."""
    conn = get_connection()
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')
    with open(schema_path, 'r') as f:
        schema = f.read()
    if config.USE_POSTGRES:
        cur = conn.cursor()
        cur.execute(schema)
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
    _exec(conn,
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
    _commit(conn)
    return node_id


def update_node(node_id, content, scores, base_score):
    """Update an existing node (for deduplication)."""
    conn = get_connection()
    now = datetime.utcnow().isoformat()
    _exec(conn,
        """UPDATE memory_nodes SET 
           content=?, sdv=?, cscv=?, aahs=?, swv=?, pdv=?,
           base_score=?, current_salience=?, updated_at=?
           WHERE id=?""",
        (content, scores.get('sdv', 0.0), scores.get('cscv', 0.0),
         scores.get('aahs', 0.0), scores.get('swv', 0.0), scores.get('pdv', 0.0),
         base_score, base_score, now, node_id)
    )
    _commit(conn)


def get_node_by_topic(user_id, topic):
    """Get a node by user+topic, or None."""
    conn = get_connection()
    cur = _exec(conn, "SELECT * FROM memory_nodes WHERE user_id=? AND topic=?", (user_id, topic))
    return _row(cur)


def get_nodes_by_user(user_id):
    """Get all nodes for a user, ordered by corrected_salience DESC."""
    conn = get_connection()
    cur = _exec(conn,
        "SELECT * FROM memory_nodes WHERE user_id=? ORDER BY corrected_salience DESC",
        (user_id,)
    )
    return _rows(cur)


def get_topic_history(topic, user_id):
    """Get prior disclosures about a topic for a user."""
    conn = get_connection()
    cur = _exec(conn,
        "SELECT content, created_at FROM memory_nodes WHERE user_id=? AND topic=? ORDER BY created_at ASC",
        (user_id, topic)
    )
    return _rows(cur)


def update_salience(node_id, new_salience):
    conn = get_connection()
    _exec(conn,
        "UPDATE memory_nodes SET current_salience=?, updated_at=? WHERE id=?",
        (new_salience, datetime.utcnow().isoformat(), node_id)
    )
    _commit(conn)


def update_corrected_salience(node_id, corrected):
    conn = get_connection()
    _exec(conn,
        "UPDATE memory_nodes SET corrected_salience=?, updated_at=? WHERE id=?",
        (corrected, datetime.utcnow().isoformat(), node_id)
    )
    _commit(conn)


def update_tds_score(node_id, tds):
    conn = get_connection()
    _exec(conn,
        "UPDATE memory_nodes SET tds_score=?, updated_at=? WHERE id=?",
        (tds, datetime.utcnow().isoformat(), node_id)
    )
    _commit(conn)


def update_decay_rate(node_id, decay_rate):
    conn = get_connection()
    _exec(conn,
        "UPDATE memory_nodes SET decay_rate=?, updated_at=? WHERE id=?",
        (decay_rate, datetime.utcnow().isoformat(), node_id)
    )
    _commit(conn)


def mark_processed(node_id):
    conn = get_connection()
    now = datetime.utcnow().isoformat()
    _exec(conn,
        """UPDATE memory_nodes SET 
           processing_count = processing_count + 1, 
           last_processed=?, updated_at=?
           WHERE id=?""",
        (now, now, node_id)
    )
    _commit(conn)


def get_all_nodes():
    conn = get_connection()
    cur = _exec(conn, "SELECT * FROM memory_nodes", ())
    return _rows(cur)


def get_all_users():
    conn = get_connection()
    cur = _exec(conn, "SELECT DISTINCT user_id FROM memory_nodes", ())
    rows = cur.fetchall()
    return [r['user_id'] for r in rows]


def delete_node(node_id):
    conn = get_connection()
    _exec(conn, "DELETE FROM memory_nodes WHERE id=?", (node_id,))
    _commit(conn)


def insert_session(user_id):
    conn = get_connection()
    session_id = str(uuid.uuid4())
    _exec(conn,
        "INSERT INTO sessions (id, user_id, started_at) VALUES (?, ?, ?)",
        (session_id, user_id, datetime.utcnow().isoformat())
    )
    _commit(conn)
    return session_id


def insert_message(session_id, user_id, role, content):
    conn = get_connection()
    msg_id = str(uuid.uuid4())
    _exec(conn,
        "INSERT INTO messages (id, session_id, user_id, role, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (msg_id, session_id, user_id, role, content, datetime.utcnow().isoformat())
    )
    _commit(conn)
    return msg_id


# ═══════════════════════════════════════════
# Study Participants
# ═══════════════════════════════════════════

def _hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def insert_study_participant(user_id, email, display_name, sandstone_panel, password=None):
    conn = get_connection()
    now = datetime.utcnow().isoformat()
    pw_hash = _hash_password(password) if password else ''
    _exec(conn,
        """INSERT INTO study_participants 
           (user_id, email, display_name, password_hash, sandstone_panel, session_count, total_exchanges, is_admin, created_at)
           VALUES (?, ?, ?, ?, ?, 0, 0, FALSE, ?)""",
        (user_id, email, display_name, pw_hash, sandstone_panel, now)
    )
    _commit(conn)
    return user_id


def get_study_participant(user_id):
    conn = get_connection()
    cur = _exec(conn, "SELECT * FROM study_participants WHERE user_id=?", (user_id,))
    return _row(cur)


def get_study_participant_by_email(email):
    conn = get_connection()
    cur = _exec(conn, "SELECT * FROM study_participants WHERE email=?", (email,))
    return _row(cur)


def get_all_study_participants():
    conn = get_connection()
    cur = _exec(conn, "SELECT * FROM study_participants ORDER BY created_at DESC", ())
    return _rows(cur)


def update_participant_session_count(user_id):
    conn = get_connection()
    _exec(conn,
        "UPDATE study_participants SET session_count = session_count + 1 WHERE user_id=?",
        (user_id,)
    )
    _commit(conn)


def update_participant_exchange_count(user_id):
    conn = get_connection()
    _exec(conn,
        "UPDATE study_participants SET total_exchanges = total_exchanges + 1 WHERE user_id=?",
        (user_id,)
    )
    _commit(conn)


def set_participant_consent(user_id):
    conn = get_connection()
    _exec(conn,
        "UPDATE study_participants SET consent_given_at=? WHERE user_id=?",
        (datetime.utcnow().isoformat(), user_id)
    )
    _commit(conn)


def set_participant_admin(user_id, is_admin=True):
    conn = get_connection()
    _exec(conn,
        "UPDATE study_participants SET is_admin=? WHERE user_id=?",
        (is_admin, user_id)
    )
    _commit(conn)


# ═══════════════════════════════════════════
# Study Ratings
# ═══════════════════════════════════════════

def insert_rating(user_id, session_number, exchange_number, message_text,
                  response_a_text, response_b_text,
                  response_a_attunement, response_a_contextual_accuracy, response_a_naturalness,
                  response_b_attunement, response_b_contextual_accuracy, response_b_naturalness,
                  preference, which_is_sandstone, memory_state_snapshot=None, model_id=None):
    conn = get_connection()
    rating_id = str(uuid.uuid4())
    snapshot_json = json.dumps(memory_state_snapshot) if memory_state_snapshot else None
    _exec(conn,
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
    _commit(conn)
    return rating_id


def get_ratings_by_user(user_id):
    conn = get_connection()
    cur = _exec(conn,
        "SELECT * FROM study_ratings WHERE user_id=? ORDER BY session_number, exchange_number",
        (user_id,)
    )
    return _rows(cur)


def get_all_ratings():
    conn = get_connection()
    cur = _exec(conn, "SELECT * FROM study_ratings ORDER BY created_at", ())
    return _rows(cur)


# ═══════════════════════════════════════════
# Conversation History
# ═══════════════════════════════════════════

def insert_conversation_turn(user_id, session_number, panel, role, content, exchange_number=0):
    conn = get_connection()
    turn_id = str(uuid.uuid4())
    _exec(conn,
        """INSERT INTO conversation_history 
           (id, user_id, session_number, panel, role, content, exchange_number, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (turn_id, user_id, session_number, panel, role, content, exchange_number,
         datetime.utcnow().isoformat())
    )
    _commit(conn)
    return turn_id


def get_conversation_history(user_id, session_number, panel):
    conn = get_connection()
    cur = _exec(conn,
        """SELECT * FROM conversation_history 
           WHERE user_id=? AND session_number=? AND panel=?
           ORDER BY created_at ASC""",
        (user_id, session_number, panel)
    )
    return _rows(cur)


def get_latest_session_number(user_id):
    conn = get_connection()
    cur = _exec(conn,
        "SELECT MAX(session_number) as max_session FROM conversation_history WHERE user_id=?",
        (user_id,)
    )
    row = _row(cur)
    if row and row.get('max_session') is not None:
        return row['max_session']
    return 0

