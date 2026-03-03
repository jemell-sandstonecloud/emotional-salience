"""
Sandstone Five-Signal Composite Legitimacy Scoring.

Signals: SDV, CSCV, AAHS, SWV, PDV
All bugs from known-issues list are fixed here.
"""

import math
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# ─── Emotional word lists (60+ words across negative and positive affect) ───

NEGATIVE_EMOTIONAL_WORDS = {
    'afraid', 'angry', 'anxious', 'ashamed', 'betrayed', 'bitter', 'broken',
    'crushed', 'depressed', 'desperate', 'devastated', 'disappointed',
    'disgusted', 'distraught', 'dread', 'empty', 'enraged', 'exhausted',
    'fearful', 'frustrated', 'furious', 'grief', 'guilty', 'heartbroken',
    'helpless', 'hopeless', 'horrified', 'humiliated', 'hurt', 'inadequate',
    'insecure', 'jealous', 'lonely', 'lost', 'miserable', 'mourning',
    'numb', 'overwhelmed', 'painful', 'panicked', 'paralyzed', 'petrified',
    'rage', 'regret', 'rejected', 'resentful', 'sad', 'scared', 'shame',
    'shattered', 'shocked', 'sorrowful', 'stressed', 'suffering', 'suicidal',
    'terrified', 'tormented', 'traumatized', 'trapped', 'ugly', 'unworthy',
    'violated', 'vulnerable', 'worthless', 'wretched', 'agonizing',
    'abandoned', 'abused', 'neglected', 'isolated', 'panicking',
}

POSITIVE_EMOTIONAL_WORDS = {
    'adored', 'alive', 'amazed', 'blessed', 'blissful', 'brave',
    'cherished', 'confident', 'content', 'delighted', 'ecstatic',
    'elated', 'empowered', 'euphoric', 'excited', 'free', 'fulfilled',
    'glad', 'grateful', 'happy', 'healed', 'hopeful', 'inspired',
    'joyful', 'liberated', 'loved', 'optimistic', 'overjoyed',
    'passionate', 'peaceful', 'proud', 'radiant', 'relieved',
    'renewed', 'safe', 'serene', 'strong', 'thankful', 'thrilled',
    'triumphant', 'uplifted', 'valued', 'warm', 'whole', 'worthy',
}

EMOTIONAL_WORDS = NEGATIVE_EMOTIONAL_WORDS | POSITIVE_EMOTIONAL_WORDS

# ─── Hedging phrases (20+) ───

HEDGING_PHRASES = [
    'i guess', 'i suppose', 'kind of', 'sort of', 'maybe', 'perhaps',
    'i think', 'i don\'t know', 'not sure', 'not really', 'whatever',
    'it\'s fine', 'no big deal', 'doesn\'t matter', 'not a big deal',
    'i mean', 'it is what it is', 'could be worse', 'probably',
    'might be', 'not that bad', 'i\'m okay', 'i\'m fine',
    'it doesn\'t bother me', 'who cares', 'anyway',
]


def count_emotional_words(text):
    """Count emotional words in text."""
    words = set(re.findall(r'\b\w+\b', text.lower()))
    return len(words & EMOTIONAL_WORDS)


def get_emotional_words(text):
    """Return the set of emotional words found in text."""
    words = set(re.findall(r'\b\w+\b', text.lower()))
    return words & EMOTIONAL_WORDS


def count_hedging_phrases(text):
    """Count hedging phrases in text."""
    text_lower = text.lower()
    return sum(1 for phrase in HEDGING_PHRASES if phrase in text_lower)


def calculate_sdv(message, session_position=0, total_session_messages=1):
    """
    Self-Disclosure Velocity.
    
    BUG FIX #4: Requires min 2 emotional words AND min 10 word count.
    Uses log scaling for message length factor. Cap at 1.0.
    """
    words = re.findall(r'\b\w+\b', message)
    word_count = len(words)
    emotional_count = count_emotional_words(message)

    # Bug fix #4: require minimum thresholds
    if emotional_count < config.MIN_EMOTIONAL_WORDS or word_count < 10:
        return 0.0

    # Emotional density
    density = emotional_count / max(word_count, 1)

    # Log scaling for message length factor (longer = more disclosure)
    length_factor = min(math.log(word_count + 1) / math.log(100), 1.0)

    # Session position factor: early disclosure = higher velocity
    if total_session_messages > 0:
        position_ratio = 1 - (session_position / total_session_messages)
    else:
        position_ratio = 1.0

    sdv = density * length_factor * (0.5 + 0.5 * position_ratio)
    return min(max(sdv, 0.0), 1.0)


def calculate_cscv(topic, user_id, current_message):
    """
    Cross-Session Consistency Variance.
    
    BUG FIX #3: Returns 1.0 when no prior history (not 0.5).
    After first session, score based on word overlap consistency.
    """
    from db.database import get_topic_history

    history = get_topic_history(topic, user_id)

    # Bug fix #3: no prior history → neutral 1.0, not penalizing 0.5
    if not history:
        return 1.0

    # Compare current message to prior disclosures
    current_words = set(re.findall(r'\b\w+\b', current_message.lower()))
    current_words -= {'i', 'me', 'my', 'the', 'a', 'an', 'is', 'was', 'it', 'to', 'and', 'of', 'in', 'that', 'for'}

    if not current_words:
        return 1.0

    overlaps = []
    for entry in history[-3:]:  # Last 3 entries
        prior_words = set(re.findall(r'\b\w+\b', entry['content'].lower()))
        prior_words -= {'i', 'me', 'my', 'the', 'a', 'an', 'is', 'was', 'it', 'to', 'and', 'of', 'in', 'that', 'for'}
        if prior_words:
            overlap = len(current_words & prior_words) / len(current_words | prior_words)
            overlaps.append(overlap)

    if not overlaps:
        return 1.0

    # Higher consistency → higher score
    return min(max(sum(overlaps) / len(overlaps), 0.0), 1.0)


def calculate_aahs(message):
    """
    Affect-Adjacent Hedging Score.
    
    Inverse of hedging density. Heavy hedging = lower score.
    Direct emotional disclosure = higher score.
    """
    hedge_count = count_hedging_phrases(message)
    word_count = len(re.findall(r'\b\w+\b', message))

    if word_count == 0:
        return 0.5

    # Hedging density normalized
    hedge_density = min(hedge_count / max(word_count / 10, 1), 1.0)

    # Inverse: more hedging = lower AAHS (less direct = less affect-salient)
    aahs = 1.0 - hedge_density
    return min(max(aahs, 0.0), 1.0)


def calculate_swv(message):
    """
    Sentiment Word Valence.
    
    Emotional word density plus exclamation and capitalization boosts.
    Each boost capped. Total capped at 1.0.
    """
    words = re.findall(r'\b\w+\b', message)
    word_count = len(words)
    emotional_count = count_emotional_words(message)

    if word_count == 0:
        return 0.0

    # Base density
    density = emotional_count / word_count

    # Exclamation boost (capped at 0.1)
    excl_count = message.count('!')
    excl_boost = min(excl_count * 0.03, 0.1)

    # Capitalization boost (capped at 0.1) — all-caps words
    caps_words = sum(1 for w in message.split() if w.isupper() and len(w) > 1)
    caps_boost = min(caps_words * 0.03, 0.1)

    swv = density + excl_boost + caps_boost
    return min(max(swv, 0.0), 1.0)


def calculate_pdv(topic, session_messages):
    """
    Proximity-Driven Volatility.
    
    Within-session mention frequency of topic. Normalized to 0-1.
    """
    if not session_messages:
        return 0.0

    topic_lower = topic.lower()
    mention_count = sum(
        1 for msg in session_messages
        if topic_lower in msg.lower()
    )

    # Normalize: mentions / total messages, capped at 1.0
    pdv = mention_count / len(session_messages)
    return min(max(pdv, 0.0), 1.0)


def calculate_base_score(sdv, cscv, aahs, swv, pdv, weights=None):
    """
    Weighted composite of all five signals.
    
    B = w1(SDV) + w2(CSCV) + w3(AAHS) + w4(SWV) + w5(PDV)
    Weights must sum to 1.0.
    """
    if weights is None:
        weights = config.DEFAULT_WEIGHTS

    assert len(weights) == 5, f"Expected 5 weights, got {len(weights)}"
    weight_sum = sum(weights)
    assert abs(weight_sum - 1.0) < 0.001, f"Weights must sum to 1.0, got {weight_sum}"

    return (
        weights[0] * sdv +
        weights[1] * cscv +
        weights[2] * aahs +
        weights[3] * swv +
        weights[4] * pdv
    )


def score_message(message, user_id, topic, session_messages=None, session_position=0, total_session_messages=1):
    """
    Score a message using all five signals plus base_score.
    
    Returns dict with sdv, cscv, aahs, swv, pdv, base_score.
    BUG FIX #7: No .pop() mutation — safe dict extraction.
    """
    if session_messages is None:
        session_messages = []

    sdv = calculate_sdv(message, session_position, total_session_messages)
    cscv = calculate_cscv(topic, user_id, message)
    aahs = calculate_aahs(message)
    swv = calculate_swv(message)
    pdv = calculate_pdv(topic, session_messages)

    base = calculate_base_score(sdv, cscv, aahs, swv, pdv)

    return {
        'sdv': sdv,
        'cscv': cscv,
        'aahs': aahs,
        'swv': swv,
        'pdv': pdv,
        'base_score': base,
    }
