"""
Sandstone Ingestion Module.

Priority-ranked topic detection, threshold enforcement, deduplication.
Bug fixes: #5 (duplicate nodes), #6 (threshold), #7 (dict mutation).
"""

import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from core.scoring import score_message, count_emotional_words
from core.tds import calculate_tds, apply_tds_correction
from db.database import (
    get_node_by_topic, insert_node, update_node,
    update_tds_score, update_corrected_salience
)

TOPIC_PRIORITY = [
    'trauma', 'abuse', 'rape', 'grief', 'loss', 'death',
    'suicide', 'self-harm', 'addiction', 'divorce', 'breakup',
    'betrayal', 'assault', 'shame', 'guilt', 'humiliation',
    'rejection', 'abandonment', 'loneliness', 'depression',
    'anxiety', 'panic', 'fear', 'anger', 'rage',
    'helplessness', 'worthlessness',
    'father', 'mother', 'parent', 'sibling', 'child',
    'partner', 'relationship', 'friendship', 'family',
    'work', 'career', 'failure', 'identity', 'purpose',
    'health', 'pain', 'body', 'trust', 'control',
]


def detect_topics(message):
    """
    Detect topics in a message using priority-ranked matching.
    Bug fix #5: Return only the SINGLE most specific match.
    """
    message_lower = message.lower()
    emotional_count = count_emotional_words(message)

    for topic in TOPIC_PRIORITY:
        pattern = r'\b' + re.escape(topic) + r'\b'
        if re.search(pattern, message_lower):
            return [topic]

    if emotional_count >= config.MIN_EMOTIONAL_WORDS:
        return ['general']

    return []


def process_message(user_id, message, session_messages=None):
    """
    Full ingestion pipeline for a message.
    Bug fix #7: Safe dict extraction — no .pop() mutation.
    """
    if session_messages is None:
        session_messages = []

    topics = detect_topics(message)
    if not topics:
        return []

    affected_node_ids = []

    for topic in topics:
        result = score_message(
            message, user_id, topic,
            session_messages=session_messages,
            session_position=len(session_messages),
            total_session_messages=max(len(session_messages), 1)
        )

        base_score = result['base_score']
        scores = {k: v for k, v in result.items() if k != 'base_score'}

        existing = get_node_by_topic(user_id, topic)

        if existing:
            if base_score >= existing['base_score']:
                update_node(existing['id'], message, scores, base_score)
            node_id = existing['id']
        else:
            emotional_count = count_emotional_words(message)
            if base_score < config.INGESTION_THRESHOLD or emotional_count < config.MIN_EMOTIONAL_WORDS:
                continue

            node_id = insert_node(user_id, topic, message, scores, base_score)

        from db.database import get_nodes_by_user
        all_nodes = get_nodes_by_user(user_id)
        tds = calculate_tds(topic, message, user_id, all_nodes)
        update_tds_score(node_id, tds)

        node = get_node_by_topic(user_id, topic)
        if node:
            corrected = apply_tds_correction(node['current_salience'], tds)
            update_corrected_salience(node_id, corrected)

        affected_node_ids.append(node_id)

    return affected_node_ids
