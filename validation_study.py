"""Sandstone Validation Study Runner.

Creates test users and runs automated validation of the scoring pipeline.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Use test database
os.environ.setdefault('DB_NAME', 'sandstone_validation')

import config
from db.database import init_db, reset_connection, get_connection
from db.database import insert_study_participant, get_nodes_by_user
from core.ingestion import process_message
from core.decay import run_decay_update, calculate_decay_rate

def clean_db():
    """Drop and recreate all tables for a clean validation run."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS conversation_history CASCADE")
        cur.execute("DROP TABLE IF EXISTS study_ratings CASCADE")
        cur.execute("DROP TABLE IF EXISTS messages CASCADE")
        cur.execute("DROP TABLE IF EXISTS sessions CASCADE")
        cur.execute("DROP TABLE IF EXISTS memory_nodes CASCADE")
        cur.execute("DROP TABLE IF EXISTS study_participants CASCADE")
    init_db()

def run_validation():
    """Run the full validation study."""
    clean_db()

    # Create test participants
    insert_study_participant("val_user_a", "val_a@test.com", "Validator A", "A", "test123")
    insert_study_participant("val_user_b", "val_b@test.com", "Validator B", "B", "test123")

    # Run test conversations
    messages = [
        ("val_user_a", "I am devastated about losing my father to grief"),
        ("val_user_a", "The anxiety about work has been overwhelming and terrifying"),
        ("val_user_a", "I still think about the trauma and feel heartbroken"),
        ("val_user_b", "My relationship with my mother is complicated and painful"),
        ("val_user_b", "I feel lonely and abandoned since the divorce"),
    ]

    for user_id, msg in messages:
        process_message(user_id, msg)
        print(f"Processed: {user_id} -> {msg[:50]}...")

    # Run decay
    updated = run_decay_update()
    print(f"\nDecay updated {updated} nodes")

    # Report
    for uid in ["val_user_a", "val_user_b"]:
        nodes = get_nodes_by_user(uid)
        print(f"\n--- {uid} ({len(nodes)} nodes) ---")
        for n in nodes:
            rate = calculate_decay_rate(n['processing_count'])
            print(f"  {n['topic']:15s} base={n['base_score']:.3f} salience={n['corrected_salience']:.3f} decay_rate={rate:.4f}")

    print("\nValidation complete.")


if __name__ == '__main__':
    run_validation()
