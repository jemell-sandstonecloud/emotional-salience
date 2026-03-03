"""
Sandstone Truth Divergence Score (TDS) — Corrective Layer.

Detects divergence between conscious reporting and underlying emotional truth.
Applied internally only — never surfaced to user.

BUG FIXES:
- ACD uses product formula, not absolute difference
- NCS returns 1.0 when no prior history
"""

import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from core.scoring import count_emotional_words, count_hedging_phrases, EMOTIONAL_WORDS, HEDGING_PHRASES


def calculate_ncs(topic, current_message, user_id):
    """
    Narrative Consistency Score.
    BUG FIX #3: Returns 1.0 when no prior history.
    """
    from db.database import get_topic_history

    history = get_topic_history(topic, user_id)

    if not history:
        return 1.0

    current_words = set(re.findall(r'\b\w+\b', current_message.lower()))
    stop_words = {'i', 'me', 'my', 'the', 'a', 'an', 'is', 'was', 'it', 'to',
                  'and', 'of', 'in', 'that', 'for', 'have', 'been', 'with', 'but',
                  'not', 'this', 'about', 'so', 'just', 'like', 'really', 'very'}
    current_words -= stop_words

    if not current_words:
        return 1.0

    overlaps = []
    for entry in history[-3:]:
        prior_words = set(re.findall(r'\b\w+\b', entry['content'].lower()))
        prior_words -= stop_words
        if prior_words:
            jaccard = len(current_words & prior_words) / len(current_words | prior_words)
            overlaps.append(jaccard)

    if not overlaps:
        return 1.0

    return min(max(sum(overlaps) / len(overlaps), 0.0), 1.0)


def calculate_acd(message):
    """
    Affect-Content Divergence.
    CRITICAL BUG FIX: Uses PRODUCT formula, not absolute difference.
    ACD = emotional_intensity × hedge_intensity
    """
    words = re.findall(r'\b\w+\b', message)
    word_count = len(words)

    if word_count == 0:
        return 0.0

    emotional_count = count_emotional_words(message)
    emotional_intensity = min(emotional_count / max(word_count / 5, 1), 1.0)

    hedge_count = count_hedging_phrases(message)
    hedge_intensity = min(hedge_count / max(word_count / 10, 1), 1.0)

    acd = emotional_intensity * hedge_intensity
    return min(max(acd, 0.0), 1.0)


def calculate_ccm(current_message, all_user_nodes):
    """Cross-topic Contradiction Metric. Placeholder for MVP — returns 0.1."""
    return 0.1


def calculate_ssi():
    """
    Somatic Signal Integration — placeholder.
    Returns 0.0 (neutral) until biometric input is integrated.
    """
    return 0.0


def calculate_tds(topic, current_message, user_id, all_nodes=None):
    """
    Weighted composite TDS score.
    TDS = w_ncs * (1-NCS) + w_acd * ACD + w_ccm * CCM + w_ssi * SSI
    """
    ncs = calculate_ncs(topic, current_message, user_id)
    acd = calculate_acd(current_message)
    ccm = calculate_ccm(current_message, all_nodes or [])
    ssi = calculate_ssi()

    weights = config.TDS_WEIGHTS
    tds = (
        weights['ncs'] * (1.0 - ncs) +
        weights['acd'] * acd +
        weights['ccm'] * ccm +
        weights['ssi'] * ssi
    )
    return min(max(tds, 0.0), 1.0)


def apply_tds_correction(salience, tds_score, delta=None):
    """
    S_corrected = S(t) × (1 - δ × TDS)
    δ = 0.3 (default). Floor at MIN_SALIENCE.
    """
    if delta is None:
        delta = config.TDS_DELTA

    corrected = salience * (1 - delta * tds_score)
    return max(corrected, config.MIN_SALIENCE)
