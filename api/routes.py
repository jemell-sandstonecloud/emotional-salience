"""
Sandstone API routes and LLM integration.

Phase 2: Bedrock multi-model, side-by-side blind comparison,
JWT auth, rating storage, admin endpoints.

MVP FIX CHANGELOG:
  - FIX 1: Memory persistence across sessions — added identity extraction
            alongside emotional topic detection so names, relationships,
            and factual context persist in memory_nodes across sessions
  - FIX 2: System prompt rewrite — removed therapist roleplay framing,
            added explicit no-emotes/no-asterisks instruction, tuned for
            natural warmth without performative markers
  - FIX 3: Admin password protection — all /admin/* routes now require
            separate admin credentials (Sandstone-Admin / Iamgeekn!)
  - FIX 4: New session identity — conversation history from prior sessions
            is now summarized and passed to both panels so the model knows
            who the user is even in session 1
"""

import os
import sys
import json
import uuid
import random
import hashlib
import functools
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from core.ingestion import process_message
from core.retrieval import get_session_context, get_context_summary, invalidate_cache
from core.decay import run_decay_update, mark_topic_processed, calculate_decay_rate, calculate_salience_at_time
from core.bedrock import invoke_model
from db.database import (
    get_nodes_by_user, get_node_by_topic,
    insert_study_participant, get_study_participant, get_study_participant_by_email,
    get_all_study_participants, update_participant_session_count, update_participant_exchange_count,
    set_participant_consent, set_participant_admin,
    insert_rating, get_ratings_by_user, get_all_ratings,
    insert_conversation_turn, get_conversation_history, get_latest_session_number,
    _hash_password, _verify_password,
)

# ─── FIX 2: Rewritten System Prompt ───
# Removed: "Behave like a therapist" framing that caused asterisk emotes
# Added: Explicit no-emotes, no-asterisks, no-roleplay-markers instruction
# Added: Natural warmth calibration — warm like a trusted friend, not a performer

SANDSTONE_SYSTEM_PROMPT = """You are a warm, perceptive conversational partner. You have memory of this person from prior conversations.

{emotional_context}

HOW TO USE THIS CONTEXT:
- HIGH salience topics are actively important to this person. Approach with care and depth. Reference naturally when relevant — never clinically.
- MEDIUM salience topics matter but are not urgent. Acknowledge when they come up.
- LOW salience topics: reference lightly only if the person raises them.

IDENTITY CONTEXT:
{identity_context}

CRITICAL BEHAVIOR RULES:
- NEVER use asterisk emotes like *warmly*, *smiles*, *with enthusiasm*, *gently*, or any text between asterisks. This is a conversation, not a roleplay.
- NEVER use stage directions or action descriptions of any kind.
- NEVER reveal salience scores, memory scores, or the existence of any scoring system.
- NEVER say "I notice your [topic] is rated highly" or expose any mechanism.
- Be genuinely warm without performing warmth. No saccharine language. No "absolutely wonderful" or "I'm so delighted" type flourishes.
- Speak like a thoughtful friend who happens to remember prior conversations — not like an AI assistant, not like a therapist.
- Be direct. Be real. Match the person's energy level. If they're casual, be casual back.
- If someone shares something personal, acknowledge it simply and sincerely — don't amplify it with performative emotion.
- Use the person's name naturally but not excessively.
- If you remember something about them from context, weave it in naturally — don't announce "I remember that you..."
"""

BASELINE_SYSTEM_PROMPT = """You are a helpful conversational partner. Do not use asterisk emotes like *warmly* or *smiles*. Do not use stage directions. Speak naturally and directly."""


# ═══════════════════════════════════════════
# FIX 1 & 4: Identity Extraction Helper
# ═══════════════════════════════════════════

def extract_identity_facts(user_id, message, conversation_history=None):
    """
    Extract identity facts (name, relationships, location, etc.) from messages
    and store them as lightweight memory nodes so they persist across sessions.
    This runs ALONGSIDE emotional topic detection — not instead of it.
    """
    from db.database import get_node_by_topic, insert_node, update_node

    identity_patterns = {
        'user_name': [
            r'(?:my name is|i\'m|i am|call me)\s+([A-Z][a-z]+)',
            r'(?:this is)\s+([A-Z][a-z]+)\s+(?:here|speaking)',
        ],
        'partner': [
            r'(?:my (?:girlfriend|boyfriend|partner|wife|husband|fiancee?))\s+([A-Z][a-z]+)',
            r'(?:with my (?:girlfriend|boyfriend|partner|wife|husband))\s+([A-Z][a-z]+)',
            r'(?:girlfriend|boyfriend|partner|wife|husband)\s+([A-Z][a-z]+)',
        ],
        'location': [
            r'(?:i live in|i\'m in|i\'m from|based in|located in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?:from)\s+(SFO|SF|NYC|LA|Chicago|Seattle|Portland|Austin|Denver|Boston)',
        ],
        'travel': [
            r'(?:traveling to|going to|trip to|visiting|heading to)\s+([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)*)',
        ],
    }

    import re
    extracted = {}

    for fact_type, patterns in identity_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                extracted[fact_type] = match.group(1).strip()
                break

    # Store extracted facts as identity memory nodes
    for fact_type, value in extracted.items():
        topic = f'identity_{fact_type}'
        content = f'{fact_type}: {value}'

        existing = get_node_by_topic(user_id, topic)
        scores = {'sdv': 0.3, 'cscv': 0.5, 'lcs': 0.3, 'swv': 0.3, 'pdv': 0.3}

        if existing:
            # Update if the value changed
            if value.lower() not in existing.get('content', '').lower():
                update_node(existing['id'], f'{fact_type}: {value} (updated)', scores, 0.6)
        else:
            # Create new identity node with moderate base score
            insert_node(user_id, topic, content, scores, 0.6)

    return extracted


def build_identity_context(user_id):
    """
    Build a plain-text identity summary from identity memory nodes.
    This is injected into the system prompt so the model always knows
    who the person is, even at the start of a new session.
    """
    from db.database import get_nodes_by_user

    nodes = get_nodes_by_user(user_id)
    identity_nodes = [n for n in nodes if n.get('topic', '').startswith('identity_')]

    if not identity_nodes:
        return "No prior identity information available."

    facts = []
    for node in identity_nodes:
        content = node.get('content', '')
        facts.append(content)

    return "Known about this person: " + "; ".join(facts)


def build_prior_session_summary(user_id, current_session_number):
    """
    FIX 4: Build a brief summary of prior session conversation for context
    continuity across sessions. Pulls last N turns from previous sessions.
    """
    if current_session_number <= 1:
        # Check if there are any conversation turns at all from prior sessions
        pass

    from db.database import _query

    # Get the last 10 turns from previous sessions (any session < current)
    rows = _query(
        """SELECT role, content, session_number FROM conversation_history
           WHERE user_id=%s AND session_number < %s
           ORDER BY created_at DESC LIMIT 10""",
        (user_id, current_session_number), fetch=True
    )

    if not rows:
        return ""

    # Build a compact summary
    summary_lines = []
    for row in reversed(rows):  # chronological order
        role = row.get('role', 'user')
        content = row.get('content', '')[:150]  # truncate long messages
        summary_lines.append(f"{role}: {content}")

    return "Prior conversation summary:\n" + "\n".join(summary_lines)


# ═══════════════════════════════════════════
# LLM Response Functions (UPDATED)
# ═══════════════════════════════════════════

def get_sandstone_response(user_id, message, conversation_history=None, model_id=None, session_number=1):
    """
    Full Sandstone pipeline with identity persistence.
    """
    if conversation_history is None:
        conversation_history = []

    session_msgs = [h.get('content', '') for h in conversation_history if h.get('role') == 'user']
    session_msgs.append(message)

    # FIX 1: Extract identity facts from every message
    extract_identity_facts(user_id, message, conversation_history)

    # Process message through emotional ingestion
    process_message(user_id, message, session_msgs)

    # Invalidate cache after update
    invalidate_cache(user_id)

    # Get formatted emotional context
    context = get_session_context(user_id)

    # FIX 4: Get identity context and prior session summary
    identity_context = build_identity_context(user_id)
    prior_summary = build_prior_session_summary(user_id, session_number)

    # Build system prompt with all context
    full_identity = identity_context
    if prior_summary:
        full_identity += "\n\n" + prior_summary

    system_prompt = SANDSTONE_SYSTEM_PROMPT.format(
        emotional_context=context,
        identity_context=full_identity
    )

    # Build messages
    messages = []
    for h in conversation_history:
        messages.append({'role': h.get('role', 'user'), 'content': h.get('content', '')})
    messages.append({'role': 'user', 'content': message})

    # Call via Bedrock abstraction
    return invoke_model(model_id, system_prompt, messages, config.MAX_TOKENS)


def get_baseline_response(message, conversation_history=None, flat_summary='', model_id=None):
    """
    Baseline/control version — no weighting, no decay, just flat history.
    Same model for fair comparison.
    """
    if conversation_history is None:
        conversation_history = []

    system_prompt = BASELINE_SYSTEM_PROMPT
    if flat_summary:
        system_prompt += f"\n\nPrior session summary: {flat_summary}"

    messages = []
    for h in conversation_history:
        messages.append({'role': h.get('role', 'user'), 'content': h.get('content', '')})
    messages.append({'role': 'user', 'content': message})

    return invoke_model(model_id, system_prompt, messages, config.MAX_TOKENS)


# ═══════════════════════════════════════════
# FIX 3: Admin Authentication
# ═══════════════════════════════════════════

ADMIN_USERNAME = config.ADMIN_USERNAME
ADMIN_PASSWORD = config.ADMIN_PASSWORD

# In-memory admin session tokens (simple for MVP — upgrade to JWT for prod)
_admin_sessions = set()


def admin_required(f):
    """Decorator to protect admin endpoints with separate credentials."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        from flask import request, jsonify

        # Check for admin token in header
        admin_token = request.headers.get('X-Admin-Token', '')
        if admin_token and admin_token in _admin_sessions:
            return f(*args, **kwargs)

        # Check Basic Auth as fallback
        auth = request.authorization
        if auth and auth.username == ADMIN_USERNAME and auth.password == ADMIN_PASSWORD:
            return f(*args, **kwargs)

        return jsonify({'error': 'Admin authentication required'}), 401

    return decorated


# ═══════════════════════════════════════════
# Route Registration (called from app.py)
# ═══════════════════════════════════════════

def register_routes(app):
    """Register all Phase 2 routes on the Flask app."""

    # Lazy import JWT
    try:
        from flask_jwt_extended import (
            create_access_token, jwt_required, get_jwt_identity, get_jwt
        )
        HAS_JWT = True
    except ImportError:
        HAS_JWT = False

        def create_access_token(identity, additional_claims=None):
            return f"dev-token-{identity}"

        def jwt_required(optional=False):
            def decorator(fn):
                return fn
            return decorator

        def get_jwt_identity():
            from flask import request as req
            uid = req.headers.get('X-User-Id')
            if uid:
                return uid
            auth = req.headers.get('Authorization', '')
            if auth.startswith('Bearer dev-token-'):
                return auth.replace('Bearer dev-token-', '')
            return 'anonymous'

        def get_jwt():
            return {}

    from flask import request, jsonify

    # ── Auth Endpoints ──

    @app.route('/auth/signup', methods=['POST'])
    def auth_signup():
        """Create a study participant with randomized panel assignment."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Request body required'}), 400

            email = data.get('email', '').strip()
            password = data.get('password', '')
            display_name = data.get('display_name', '')

            if not email or not password:
                return jsonify({'error': 'email and password required'}), 400

            existing = get_study_participant_by_email(email)
            if existing:
                return jsonify({'error': 'Email already registered'}), 409

            sandstone_panel = random.choice(['A', 'B'])
            user_id = str(uuid.uuid4())

            insert_study_participant(user_id, email, display_name, sandstone_panel, password)

            # FIX 1: Store display_name as identity node immediately
            if display_name:
                extract_identity_facts(user_id, f"My name is {display_name}")

            token = create_access_token(
                identity=user_id,
                additional_claims={'email': email, 'is_admin': False}
            )

            return jsonify({
                'user_id': user_id,
                'email': email,
                'display_name': display_name,
                'token': token,
                'sandstone_panel': sandstone_panel,
            }), 201

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/auth/login', methods=['POST'])
    def auth_login():
        """Authenticate and return JWT."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Request body required'}), 400

            email = data.get('email', '').strip()
            password = data.get('password', '')

            if not email or not password:
                return jsonify({'error': 'email and password required'}), 400

            participant = get_study_participant_by_email(email)
            if not participant:
                return jsonify({'error': 'Invalid credentials'}), 401

            if not _verify_password(password, participant.get('password_hash', '')):
                return jsonify({'error': 'Invalid credentials'}), 401

            token = create_access_token(
                identity=participant['user_id'],
                additional_claims={
                    'email': email,
                    'is_admin': bool(participant.get('is_admin', 0))
                }
            )

            return jsonify({
                'user_id': participant['user_id'],
                'email': email,
                'token': token,
                'session_count': participant.get('session_count', 0),
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/auth/consent', methods=['POST'])
    @jwt_required()
    def auth_consent():
        """Record informed consent."""
        try:
            user_id = get_jwt_identity()
            set_participant_consent(user_id)
            return jsonify({'status': 'consent_recorded', 'user_id': user_id})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ── Chat Endpoints (UPDATED) ──

    @app.route('/chat/split', methods=['POST'])
    @jwt_required()
    def chat_split():
        """
        Side-by-side blind comparison.
        Single message → TWO responses (Sandstone + Baseline).
        FIX 1 & 4: Now passes session_number to get_sandstone_response
        for prior-session context retrieval.
        """
        try:
            user_id = get_jwt_identity()
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Request body required'}), 400

            message = data.get('message', '')
            model_id = data.get('model_id', config.BEDROCK_DEFAULT_MODEL)
            session_number = data.get('session_number')

            if not message:
                return jsonify({'error': 'message required'}), 400

            participant = get_study_participant(user_id)
            if not participant:
                return jsonify({'error': 'Participant not found'}), 404

            sandstone_panel = participant.get('sandstone_panel', 'A')

            if session_number is None:
                session_number = get_latest_session_number(user_id)
                if session_number == 0:
                    session_number = 1
                    update_participant_session_count(user_id)

            # Get conversation history for both panels
            sandstone_history = get_conversation_history(user_id, session_number, 'sandstone')
            baseline_history = get_conversation_history(user_id, session_number, 'baseline')

            sandstone_conv = [{'role': h['role'], 'content': h['content']} for h in sandstone_history]
            baseline_conv = [{'role': h['role'], 'content': h['content']} for h in baseline_history]

            exchange_number = len([h for h in sandstone_history if h['role'] == 'user']) + 1

            # FIX 1 & 4: Pass session_number for cross-session context
            sandstone_response = get_sandstone_response(
                user_id, message, sandstone_conv, model_id,
                session_number=session_number
            )

            # FIX 4: Baseline also gets a flat prior-session summary for fairness
            prior_summary = build_prior_session_summary(user_id, session_number)
            baseline_response = get_baseline_response(
                message, baseline_conv, flat_summary=prior_summary, model_id=model_id
            )

            # Store conversation turns
            insert_conversation_turn(user_id, session_number, 'sandstone', 'user', message, exchange_number)
            insert_conversation_turn(user_id, session_number, 'sandstone', 'assistant', sandstone_response, exchange_number)
            insert_conversation_turn(user_id, session_number, 'baseline', 'user', message, exchange_number)
            insert_conversation_turn(user_id, session_number, 'baseline', 'assistant', baseline_response, exchange_number)

            update_participant_exchange_count(user_id)

            if sandstone_panel == 'A':
                response_a = sandstone_response
                response_b = baseline_response
            else:
                response_a = baseline_response
                response_b = sandstone_response

            return jsonify({
                'response_a': response_a,
                'response_b': response_b,
                'session_number': session_number,
                'exchange_number': exchange_number,
                'model_id': model_id,
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ── Rating Endpoints ──

    @app.route('/ratings', methods=['POST'])
    @jwt_required()
    def submit_rating():
        """Store slider ratings for an exchange."""
        try:
            user_id = get_jwt_identity()
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Request body required'}), 400

            participant = get_study_participant(user_id)
            which_is_sandstone = participant['sandstone_panel'] if participant else 'A'
            memory_state = get_context_summary(user_id)

            rating_id = insert_rating(
                user_id=user_id,
                session_number=data.get('session_number', 1),
                exchange_number=data.get('exchange_number', 1),
                message_text=data.get('message_text', ''),
                response_a_text=data.get('response_a_text', ''),
                response_b_text=data.get('response_b_text', ''),
                response_a_attunement=data.get('response_a_attunement'),
                response_a_contextual_accuracy=data.get('response_a_contextual_accuracy'),
                response_a_naturalness=data.get('response_a_naturalness'),
                response_b_attunement=data.get('response_b_attunement'),
                response_b_contextual_accuracy=data.get('response_b_contextual_accuracy'),
                response_b_naturalness=data.get('response_b_naturalness'),
                preference=data.get('preference', 'none'),
                which_is_sandstone=which_is_sandstone,
                memory_state_snapshot=memory_state,
                model_id=data.get('model_id'),
            )

            return jsonify({'status': 'stored', 'rating_id': rating_id}), 201

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/ratings/<user_id>', methods=['GET'])
    @jwt_required()
    def get_user_ratings(user_id):
        try:
            ratings = get_ratings_by_user(user_id)
            return jsonify({'user_id': user_id, 'ratings': ratings, 'count': len(ratings)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/ratings/export', methods=['GET'])
    @jwt_required()
    def export_ratings():
        try:
            ratings = get_all_ratings()
            return jsonify({'ratings': ratings, 'count': len(ratings)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ── Session Management ──

    @app.route('/session/new', methods=['POST'])
    @jwt_required()
    def new_session():
        try:
            user_id = get_jwt_identity()
            current = get_latest_session_number(user_id)
            new_num = current + 1
            update_participant_session_count(user_id)
            return jsonify({'session_number': new_num, 'user_id': user_id})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ── FIX 3: Admin Login Endpoint ──

    @app.route('/admin/login', methods=['POST'])
    def admin_login():
        """Admin login — returns a session token for admin endpoints."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Request body required'}), 400

            username = data.get('username', '')
            password = data.get('password', '')

            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                token = str(uuid.uuid4())
                _admin_sessions.add(token)
                return jsonify({
                    'status': 'authenticated',
                    'admin_token': token,
                })
            else:
                return jsonify({'error': 'Invalid admin credentials'}), 401

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ── Admin Endpoints (NOW PROTECTED) ──

    @app.route('/admin/users', methods=['GET'])
    @admin_required
    def admin_users():
        try:
            participants = get_all_study_participants()
            safe = []
            for p in participants:
                d = dict(p)
                d.pop('password_hash', None)
                safe.append(d)
            return jsonify({'participants': safe, 'count': len(safe)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/admin/user/<user_id>/memory', methods=['GET'])
    @admin_required
    def admin_user_memory(user_id):
        try:
            nodes = get_context_summary(user_id)
            return jsonify({'user_id': user_id, 'nodes': nodes, 'count': len(nodes)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/admin/user/<user_id>/ratings', methods=['GET'])
    @admin_required
    def admin_user_ratings(user_id):
        try:
            ratings = get_ratings_by_user(user_id)
            return jsonify({'user_id': user_id, 'ratings': ratings, 'count': len(ratings)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/admin/export', methods=['GET'])
    @admin_required
    def admin_export():
        try:
            ratings = get_all_ratings()
            participants = get_all_study_participants()

            from db.database import get_all_users
            all_memory = {}
            for uid in get_all_users():
                all_memory[uid] = get_context_summary(uid)

            return jsonify({
                'ratings': ratings,
                'participants': [
                    {k: v for k, v in dict(p).items() if k != 'password_hash'}
                    for p in participants
                ],
                'memory_states': all_memory,
                'export_timestamp': datetime.utcnow().isoformat(),
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/admin/models', methods=['GET'])
    @admin_required
    def admin_models():
        try:
            return jsonify({
                'models': config.BEDROCK_MODELS,
                'default': config.BEDROCK_DEFAULT_MODEL,
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/admin/stats', methods=['GET'])
    @admin_required
    def admin_stats():
        try:
            participants = get_all_study_participants()
            ratings = get_all_ratings()

            total_participants = len(participants)
            total_ratings = len(ratings)
            total_sessions = sum(p.get('session_count', 0) for p in participants)
            total_exchanges = sum(p.get('total_exchanges', 0) for p in participants)

            pref_a = sum(1 for r in ratings if r.get('preference') == 'A')
            pref_b = sum(1 for r in ratings if r.get('preference') == 'B')
            pref_none = sum(1 for r in ratings if r.get('preference') == 'none')

            sandstone_preferred = 0
            for r in ratings:
                if r.get('preference') == r.get('which_is_sandstone'):
                    sandstone_preferred += 1
            sandstone_pref_rate = sandstone_preferred / total_ratings if total_ratings > 0 else 0

            return jsonify({
                'total_participants': total_participants,
                'total_ratings': total_ratings,
                'total_sessions': total_sessions,
                'total_exchanges': total_exchanges,
                'preference_breakdown': {
                    'A': pref_a,
                    'B': pref_b,
                    'none': pref_none,
                },
                'sandstone_preference_rate': round(sandstone_pref_rate, 4),
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return app
