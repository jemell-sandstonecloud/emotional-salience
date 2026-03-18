"""
Sandstone Processing-Frequency-Modulated Decay Engine.

Core patent claim: S(t) = B × e^(-λt) + κ(θ)
Lambda increases with processing count: λ = BASE_DECAY_RATE × (1 + processing_count × PROCESSING_BOOST)
"""

import math
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def parse_timestamp(ts):
    """Parse timestamp — handles ISO format and PostgreSQL CURRENT_TIMESTAMP."""
    if isinstance(ts, datetime):
        return ts
    for fmt in (
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f',
    ):
        try:
            return datetime.strptime(ts, fmt)
        except (ValueError, TypeError):
            continue
    raise ValueError(f"Cannot parse timestamp: {ts}")


def calculate_decay_rate(processing_count, base_rate=None):
    """
    λ = base_rate × (1 + processing_count × PROCESSING_BOOST)
    PROCESSING_BOOST must be 0.5 (bug fix #2).
    """
    if base_rate is None:
        base_rate = config.BASE_DECAY_RATE
    return base_rate * (1 + processing_count * config.PROCESSING_BOOST)


def calculate_salience(base_score, created_at, decay_rate, spike=0.0):
    """
    S(t) = B × e^(-λt) + κ
    
    t is in days since creation.
    Floor at MIN_SALIENCE.
    """
    now = datetime.utcnow()
    created = parse_timestamp(created_at)
    days_elapsed = max((now - created).total_seconds() / 86400, 0)

    salience = base_score * math.exp(-decay_rate * days_elapsed) + spike
    return max(salience, config.MIN_SALIENCE)


def calculate_salience_at_time(base_score, days_elapsed, decay_rate, spike=0.0):
    """Calculate salience at a specific number of days elapsed (for testing)."""
    salience = base_score * math.exp(-decay_rate * days_elapsed) + spike
    return max(salience, config.MIN_SALIENCE)


def apply_spike(node, increment=0.15, cap=0.5):
    """Apply temporary salience boost when topic mentioned in session."""
    current_spike = node.get('spike_coefficient', 0.0)
    new_spike = min(current_spike + increment, cap)
    return new_spike


def decay_spike(spike, days_since_mention, half_life=3):
    """Spike decays separately with its own half-life."""
    if spike <= 0 or days_since_mention <= 0:
        return spike
    decay_factor = math.exp(-0.693 * days_since_mention / half_life)
    return spike * decay_factor


def run_decay_update():
    """
    Iterate all nodes, recalculate decay_rate and salience, update DB.
    Returns count of updated nodes.
    """
    from db.database import get_all_nodes, update_salience, update_decay_rate, update_corrected_salience
    from core.lds import apply_lds_correction

    nodes = get_all_nodes()
    updated = 0

    for node in nodes:
        new_decay_rate = calculate_decay_rate(node['processing_count'])
        update_decay_rate(node['id'], new_decay_rate)

        new_salience = calculate_salience(
            node['base_score'],
            node['created_at'],
            new_decay_rate,
            node.get('spike_coefficient', 0.0)
        )
        update_salience(node['id'], new_salience)

        corrected = apply_lds_correction(new_salience, node.get('lds_score', 0.0))
        update_corrected_salience(node['id'], corrected)

        updated += 1

    return updated


def mark_topic_processed(node_id):
    """Increment processing_count in DB."""
    from db.database import mark_processed
    mark_processed(node_id)


def archive_cold_nodes(threshold=None):
    """Archive nodes below threshold to S3 (if configured)."""
    if threshold is None:
        threshold = config.ARCHIVE_THRESHOLD

    from db.database import get_all_nodes, delete_node

    nodes = get_all_nodes()
    archived = 0

    for node in nodes:
        if node['corrected_salience'] < threshold:
            try:
                import boto3
                s3 = boto3.client('s3', region_name=config.AWS_DEFAULT_REGION)
                import json
                s3.put_object(
                    Bucket=config.ARCHIVE_BUCKET,
                    Key=f"archived/{node['user_id']}/{node['id']}.json",
                    Body=json.dumps(dict(node), default=str)
                )
                delete_node(node['id'])
                archived += 1
            except Exception:
                pass

    return archived
