"""Sandstone Retrieval Layer — context formatting for LLM injection."""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from db.database import get_nodes_by_user


def get_salience_label(salience):
    """Classify salience into HIGH/MEDIUM/LOW."""
    if salience > 0.6:
        return 'HIGH'
    elif salience >= 0.3:
        return 'MEDIUM'
    else:
        return 'LOW'


def format_context(nodes):
    """Format nodes for LLM injection."""
    if not nodes:
        return "[EMOTIONAL MEMORY CONTEXT — No prior emotional context available]\n[END CONTEXT]"

    lines = ["[EMOTIONAL MEMORY CONTEXT — Use this to inform your responses]"]

    for node in nodes:
        salience = node.get('corrected_salience', node.get('current_salience', 0))
        label = get_salience_label(salience)
        topic = node.get('topic', 'UNKNOWN').upper()
        content = node.get('content', '')[:200]
        lines.append(f"[{label} SALIENCE: {salience:.2f}] Topic: {topic} — {content}")

    lines.append("[END CONTEXT]")
    return '\n'.join(lines)


def get_session_context(user_id, top_n=5):
    """Get formatted context for a user session."""
    if config.REDIS_ENABLED:
        try:
            import redis
            r = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True)
            cached = r.get(f'sandstone:context:{user_id}')
            if cached:
                return cached
        except Exception:
            pass

    nodes = get_nodes_by_user(user_id)[:top_n]
    context = format_context(nodes)

    if config.REDIS_ENABLED:
        try:
            import redis
            r = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True)
            r.setex(f'sandstone:context:{user_id}', 300, context)
        except Exception:
            pass

    return context


def invalidate_cache(user_id):
    """Clear Redis cache for a user."""
    if config.REDIS_ENABLED:
        try:
            import redis
            r = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True)
            r.delete(f'sandstone:context:{user_id}')
        except Exception:
            pass


def get_context_summary(user_id):
    """Admin/debug view — full node state as dict list."""
    nodes = get_nodes_by_user(user_id)
    return [
        {
            'id': n['id'],
            'topic': n['topic'],
            'base_score': n['base_score'],
            'current_salience': n['current_salience'],
            'corrected_salience': n['corrected_salience'],
            'lds_score': n['lds_score'],
            'processing_count': n['processing_count'],
            'decay_rate': n['decay_rate'],
            'spike_coefficient': n['spike_coefficient'],
            'content_preview': n['content'][:100],
            'created_at': n['created_at'],
        }
        for n in nodes
    ]
