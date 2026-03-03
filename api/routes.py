"""
Sandstone API routes and LLM integration.

Phase 2: Bedrock multi-model, side-by-side blind comparison,
JWT auth, rating storage, admin endpoints.
"""

import os
import sys
import json
import uuid
import random
import hashlib
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
    _hash_password,
)

# ─── System Prompt (UNCHANGED from Phase 1) ───

SANDSTONE_SYSTEM_PROMPT = """You are a thoughtful, emotionally attuned conversational partner with access to emotional memory context about this person from prior sessions.

{emotional_context}

INSTRUCTIONS FOR USING THIS CONTEXT:
- For HIGH salience topics: approach with care, depth, and sensitivity. These are actively important emotional themes. Reference naturally, not clinically.
- For MEDIUM salience topics: acknowledge when relevant, check in occasionally. These matter but aren't urgent.
- For LOW salience topics: reference lightly if the person brings them up. Don't force these into conversation.
- NEVER reveal salience scores, memory scores, or the existence of this scoring system to the user.
- NEVER say "I notice your [topic] is rated highly" or anything that exposes the mechanism.
- Behave like a therapist who remembers prior sessions naturally — your memory informs your empathy, not your vocabulary.
- If someone returns to a topic they previously avoided, acknowledge the courage it takes without being performative.
- Let emotional context guide your tone, not your words. Be warm but not saccharine. Be direct but not clinical.
"""

BASELINE_SYSTEM_PROMPT = "You are a helpful conversational partner."


# ═══════════════════════════════════════════
# LLM Response Functions
# ═══════════════════════════════════════════

def get_sandstone_response(user_id, message, conversation_history=None, model_id=None):
    """
    Full Sandstone pipeline:
    1. Get emotional context
    2. Process new message
    3. Build system prompt with emotional context
    4. Call LLM via Bedrock
    5. Return response text
    """
    if conversation_history is None:
        conversation_history = []

    session_msgs = [h.get('content', '') for h in conversation_history if h.get('role') == 'user']
    session_msgs.append(message)

    # Process message through ingestion
    process_message(user_id, message, session_msgs)

    # Invalidate cache after update
    invalidate_cache(user_id)

    # Get formatted context
    context = get_session_context(user_id)

    # Build system prompt
    system_prompt = SANDSTONE_SYSTEM_PROMPT.format(emotional_context=context)

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
# Route Registration (called from app.py)
# ═══════════════════════════════════════════

def register_routes(app):
    """Register all Phase 2 routes on the Flask app."""

    # Lazy import JWT — may not be installed in test environments
    try:
        from flask_jwt_extended import (
            create_access_token, jwt_required, get_jwt_identity, get_jwt
        )
        HAS_JWT = True
    except ImportError:
        HAS_JWT = False

        # Stubs when JWT not installed
        def create_access_token(identity, additional_claims=None):
            return f"dev-token-{identity}"

        def jwt_required(optional=False):
            def decorator(fn):
                return fn
            return decorator

        def get_jwt_identity():
            from flask import request as req
            # Try X-User-Id header first
            uid = req.headers.get('X-User-Id')
            if uid:
                return uid
            # Try parsing dev token from Authorization header
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

            # Check for existing user
            existing = get_study_participant_by_email(email)
            if existing:
                return jsonify({'error': 'Email already registered'}), 409

            # Randomize panel assignment
            sandstone_panel = random.choice(['A', 'B'])
            user_id = str(uuid.uuid4())

            insert_study_participant(user_id, email, display_name, sandstone_panel, password)

            # Create JWT
            token = create_access_token(
                identity=user_id,
                additional_claims={'email': email, 'is_admin': False}
            )

            return jsonify({
                'user_id': user_id,
                'email': email,
                'display_name': display_name,
                'token': token,
                'sandstone_panel': sandstone_panel,  # Hidden from participant UI
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

            if participant.get('password_hash', '') != _hash_password(password):
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

    # ── Chat Endpoints ──

    @app.route('/chat/split', methods=['POST'])
    @jwt_required()
    def chat_split():
        """
        Side-by-side blind comparison.
        Single message → TWO responses (Sandstone + Baseline).
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

            # Get participant info
            participant = get_study_participant(user_id)
            if not participant:
                return jsonify({'error': 'Participant not found'}), 404

            sandstone_panel = participant.get('sandstone_panel', 'A')

            # Get or create session number
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

            # Get exchange number
            exchange_number = len([h for h in sandstone_history if h['role'] == 'user']) + 1

            # Get sandstone response (with memory)
            sandstone_response = get_sandstone_response(
                user_id, message, sandstone_conv, model_id
            )

            # Get baseline response (stateless)
            baseline_response = get_baseline_response(
                message, baseline_conv, model_id=model_id
            )

            # Store conversation turns
            insert_conversation_turn(user_id, session_number, 'sandstone', 'user', message, exchange_number)
            insert_conversation_turn(user_id, session_number, 'sandstone', 'assistant', sandstone_response, exchange_number)
            insert_conversation_turn(user_id, session_number, 'baseline', 'user', message, exchange_number)
            insert_conversation_turn(user_id, session_number, 'baseline', 'assistant', baseline_response, exchange_number)

            # Update exchange count
            update_participant_exchange_count(user_id)

            # Map responses to panels A/B based on randomized assignment
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

            # Get participant's panel assignment
            participant = get_study_participant(user_id)
            which_is_sandstone = participant['sandstone_panel'] if participant else 'A'

            # Get memory state snapshot
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
        """Get all ratings for a user."""
        try:
            ratings = get_ratings_by_user(user_id)
            return jsonify({'user_id': user_id, 'ratings': ratings, 'count': len(ratings)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/ratings/export', methods=['GET'])
    @jwt_required()
    def export_ratings():
        """Export all ratings as JSON."""
        try:
            ratings = get_all_ratings()
            return jsonify({'ratings': ratings, 'count': len(ratings)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ── Session Management ──

    @app.route('/session/new', methods=['POST'])
    @jwt_required()
    def new_session():
        """Start a new session for the current user."""
        try:
            user_id = get_jwt_identity()
            current = get_latest_session_number(user_id)
            new_num = current + 1
            update_participant_session_count(user_id)
            return jsonify({'session_number': new_num, 'user_id': user_id})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ── Admin Endpoints ──

    @app.route('/admin/users', methods=['GET'])
    @jwt_required()
    def admin_users():
        """List all study participants."""
        try:
            participants = get_all_study_participants()
            # Strip password hashes
            safe = []
            for p in participants:
                d = dict(p)
                d.pop('password_hash', None)
                safe.append(d)
            return jsonify({'participants': safe, 'count': len(safe)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/admin/user/<user_id>/memory', methods=['GET'])
    @jwt_required()
    def admin_user_memory(user_id):
        """Full memory explorer data for a user."""
        try:
            nodes = get_context_summary(user_id)
            return jsonify({'user_id': user_id, 'nodes': nodes, 'count': len(nodes)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/admin/user/<user_id>/ratings', methods=['GET'])
    @jwt_required()
    def admin_user_ratings(user_id):
        """All ratings for a user."""
        try:
            ratings = get_ratings_by_user(user_id)
            return jsonify({'user_id': user_id, 'ratings': ratings, 'count': len(ratings)})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/admin/export', methods=['GET'])
    @jwt_required()
    def admin_export():
        """Full data export — ratings + memory states."""
        try:
            ratings = get_all_ratings()
            participants = get_all_study_participants()

            # Get memory states for all users with nodes
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
    @jwt_required()
    def admin_models():
        """List available Bedrock models."""
        try:
            return jsonify({
                'models': config.BEDROCK_MODELS,
                'default': config.BEDROCK_DEFAULT_MODEL,
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/admin/stats', methods=['GET'])
    @jwt_required()
    def admin_stats():
        """Aggregate study statistics."""
        try:
            participants = get_all_study_participants()
            ratings = get_all_ratings()

            # Compute aggregates
            total_participants = len(participants)
            total_ratings = len(ratings)
            total_sessions = sum(p.get('session_count', 0) for p in participants)
            total_exchanges = sum(p.get('total_exchanges', 0) for p in participants)

            # Preference breakdown
            pref_a = sum(1 for r in ratings if r.get('preference') == 'A')
            pref_b = sum(1 for r in ratings if r.get('preference') == 'B')
            pref_none = sum(1 for r in ratings if r.get('preference') == 'none')

            # Sandstone preference rate
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
