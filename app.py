"""Sandstone Flask Application — Phase 2."""

import os
import sys
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
import config
from db.database import init_db, get_nodes_by_user, mark_processed, insert_session, insert_message
from core.retrieval import get_context_summary
from core.decay import run_decay_update
from api.routes import get_sandstone_response, get_baseline_response, register_routes

app = Flask(__name__)

# ─── JWT Configuration ───
app.config['JWT_SECRET_KEY'] = config.JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# ─── CORS ───
try:
    from flask_cors import CORS
    CORS(app, origins=config.CORS_ORIGINS)
except ImportError:
    print("[WARN] flask-cors not installed — CORS disabled.")

# ─── JWT ───
try:
    from flask_jwt_extended import JWTManager
    jwt = JWTManager(app)
except ImportError:
    print("[WARN] flask-jwt-extended not installed — JWT auth disabled.")

# ─── Rate Limiting ───
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per hour"],
        storage_uri="memory://",
    )
except ImportError:
    print("[WARN] flask-limiter not installed — rate limiting disabled.")

# ─── Background Decay Scheduler ───
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=run_decay_update,
        trigger='interval',
        hours=config.DECAY_SCHEDULE_HOURS,
        id='decay_update'
    )
    scheduler.start()
except ImportError:
    print("[WARN] APScheduler not installed — background decay disabled.")


# ─── Core Endpoints (backward compatible) ───

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})


@app.route('/chat', methods=['POST'])
def chat():
    """Sandstone version — emotionally weighted memory."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400

        user_id = data.get('user_id')
        message = data.get('message')
        history = data.get('history', [])
        model_id = data.get('model_id')

        if not user_id or not message:
            return jsonify({'error': 'user_id and message required'}), 400

        try:
            session_id = insert_session(user_id)
            insert_message(session_id, user_id, 'user', message)
        except Exception:
            pass

        response_text = get_sandstone_response(user_id, message, history, model_id)

        return jsonify({
            'response': response_text,
            'user_id': user_id,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/chat/baseline', methods=['POST'])
def chat_baseline():
    """Control version — no weighting, no decay."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400

        message = data.get('message')
        history = data.get('history', [])
        flat_summary = data.get('flat_summary', '')
        model_id = data.get('model_id')

        if not message:
            return jsonify({'error': 'message required'}), 400

        response_text = get_baseline_response(message, history, flat_summary, model_id)
        return jsonify({'response': response_text})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/memory/<user_id>', methods=['GET'])
def memory(user_id):
    """Admin: view current memory state."""
    try:
        summary = get_context_summary(user_id)
        return jsonify({'user_id': user_id, 'nodes': summary, 'count': len(summary)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/memory/<user_id>/process/<node_id>', methods=['POST'])
def process_topic(user_id, node_id):
    """Mark a topic as therapeutically processed."""
    try:
        mark_processed(node_id)
        return jsonify({'status': 'processed', 'node_id': node_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/decay/run', methods=['POST'])
def trigger_decay():
    """Manually trigger decay update."""
    try:
        count = run_decay_update()
        return jsonify({'status': 'complete', 'nodes_updated': count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── Register Phase 2 Routes ───
register_routes(app)


if __name__ == '__main__':
    init_db()
    print("Sandstone Phase 2 initialized. Starting server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
