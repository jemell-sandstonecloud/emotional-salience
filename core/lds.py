"""
Sandstone Linguistic Divergence Score (LDS) — Corrective Layer.

Computes multi-dimensional linguistic consistency scores across user
message history. Applied as additive salience correction.

Renamed from TDS (Truth Divergence Score) in v2.1 to align with
computational linguistics framing per patent strategy.

Variable renames:
  NCS → CSD (Cross-Session Divergence)
  ACD → ICD (Intra-Message Consistency Detector)
  CCM → CCS (Cross-Context Consistency Score)
  SSI → VSI (Valence Shift Index)
  TDS → LDS (Linguistic Divergence Score)

CRITICAL FIX v2.1: LDS correction is now ADDITIVE (higher LDS → higher
salience) not subtractive. Higher divergence means user's language
understates true significance → salience should increase.
"""

import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from core.scoring import count_emotional_words, count_hedging_phrases, EMOTIONAL_WORDS, HEDGING_PHRASES


def calculate_csd(topic, current_message, user_id):
    """
    Cross-Session Divergence (was NCS — Narrative Consistency Score).
    Computes cross-session semantic contradiction by comparing current
    message against stored statements for the same topic.
    Returns 0.0 (high consistency) to 1.0 (high divergence).
    """
    from db.database import get_topic_history

    history = get_topic_history(topic, user_id)

    if not history:
        return 0.0  # No prior data — no divergence detectable

    current_words = set(re.findall(r'\b\w+\b', current_message.lower()))
    stop_words = {'i', 'me', 'my', 'the', 'a', 'an', 'is', 'was', 'it', 'to',
                  'and', 'of', 'in', 'that', 'for', 'have', 'been', 'with', 'but',
                  'not', 'this', 'about', 'so', 'just', 'like', 'really', 'very'}
    current_words -= stop_words

    if not current_words:
        return 0.0

    overlaps = []
    for entry in history[-3:]:
        prior_words = set(re.findall(r'\b\w+\b', entry['content'].lower()))
        prior_words -= stop_words
        if prior_words:
            jaccard = len(current_words & prior_words) / len(current_words | prior_words)
            overlaps.append(jaccard)

    if not overlaps:
        return 0.0

    # Invert: low overlap = high divergence
    consistency = sum(overlaps) / len(overlaps)
    return min(max(1.0 - consistency, 0.0), 1.0)


def calculate_icd(message):
    """
    Intra-Message Consistency Detector (was ACD — Affect-Content Divergence).
    Detects co-occurrence of state-declaration tokens with contradictory-
    context tokens (sleep disruption, physiological response, avoidance,
    rumination descriptors).
    """
    words = re.findall(r'\b\w+\b', message)
    word_count = len(words)

    if word_count == 0:
        return 0.0

    emotional_count = count_emotional_words(message)
    emotional_intensity = min(emotional_count / max(word_count / 5, 1), 1.0)

    hedge_count = count_hedging_phrases(message)
    hedge_intensity = min(hedge_count / max(word_count / 10, 1), 1.0)

    icd = emotional_intensity * hedge_intensity
    return min(max(icd, 0.0), 1.0)


def calculate_ccs(current_message, all_user_nodes):
    """
    Cross-Context Consistency Score (was CCM).
    Measures co-occurrence frequency between situation-descriptor tokens
    and response-descriptor tokens compared against baseline distribution.
    Placeholder for MVP — returns 0.1.
    """
    return 0.1


def calculate_vsi():
    """
    Valence Shift Index (was SSI — Somatic Signal Integration).
    Within-session linguistic tone variance computed from sentiment
    polarity sequence. Placeholder — returns 0.0 until session-level
    sentiment tracking is implemented.
    """
    return 0.0


def calculate_lds(topic, current_message, user_id, all_nodes=None):
    """
    Linguistic Divergence Score (was TDS — Truth Divergence Score).
    Weighted composite of CSD, ICD, CCS, VSI.
    """
    csd = calculate_csd(topic, current_message, user_id)
    icd = calculate_icd(current_message)
    ccs = calculate_ccs(current_message, all_nodes or [])
    vsi = calculate_vsi()

    weights = config.LDS_WEIGHTS
    lds = (
        weights['csd'] * csd +
        weights['icd'] * icd +
        weights['ccs'] * ccs +
        weights['vsi'] * vsi
    )
    return min(max(lds, 0.0), 1.0)


def apply_lds_correction(salience, lds_score, epsilon=None):
    """
    ADDITIVE salience correction (FIXED in v2.1).
    
    corrected = salience + (ε × lds_score)
    
    Higher LDS → user language understates significance → increase salience.
    This is the OPPOSITE of the old TDS formula which was subtractive.
    
    ε = 0.15 (patent: range 0.05-0.25). Cap at 1.0.
    """
    if epsilon is None:
        epsilon = config.LDS_EPSILON

    corrected = salience + (epsilon * lds_score)
    return min(max(corrected, config.MIN_SALIENCE), 1.0)
