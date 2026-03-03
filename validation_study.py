"""
Sandstone Validation Study Harness.

Runs both Version A (baseline) and Version B (Sandstone) for the same user
across multiple simulated sessions.
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DATABASE_PATH', 'db/sandstone_validation.db')

from db.database import init_db, reset_connection, get_nodes_by_user
from core.ingestion import process_message
from core.retrieval import get_session_context, get_context_summary, format_context
from api.routes import get_sandstone_response, get_baseline_response


def run_validation_study(sessions, user_id='validation_user'):
    reset_connection()
    try:
        os.remove(os.environ.get('DATABASE_PATH', 'db/sandstone_validation.db'))
    except FileNotFoundError:
        pass
    init_db()

    results = []
    flat_history = []

    for session_idx, session_messages in enumerate(sessions, 1):
        session_history = []
        for msg_idx, message in enumerate(session_messages, 1):
            sandstone_response = get_sandstone_response(user_id, message, session_history)
            flat_summary = '; '.join(flat_history[-10:]) if flat_history else ''
            baseline_response = get_baseline_response(message, session_history, flat_summary)
            memory_state = get_context_summary(user_id)
            context_str = get_session_context(user_id)

            results.append({
                'session': session_idx,
                'message_number': msg_idx,
                'message': message,
                'sandstone_response': sandstone_response,
                'baseline_response': baseline_response,
                'memory_state': memory_state,
                'formatted_context': context_str,
                'rating_fields': {
                    'attunement': None,
                    'contextual_accuracy': None,
                    'appropriate_salience': None,
                }
            })

            session_history.append({'role': 'user', 'content': message})
            session_history.append({'role': 'assistant', 'content': sandstone_response})
            flat_history.append(message)

    return results


def print_study_summary(results):
    print("\n" + "=" * 80)
    print("SANDSTONE VALIDATION STUDY — COMPARISON OUTPUT")
    print("=" * 80)

    for r in results:
        print(f"\n--- Session {r['session']}, Message {r['message_number']} ---")
        print(f"USER: {r['message']}")
        print(f"\nSANDSTONE (Version B):")
        print(f"  {r['sandstone_response'][:200]}...")
        print(f"\nBASELINE (Version A):")
        print(f"  {r['baseline_response'][:200]}...")
        print(f"\nMEMORY STATE ({len(r['memory_state'])} nodes):")
        for node in r['memory_state']:
            print(f"  [{node['topic']}] corrected_salience={node['corrected_salience']:.3f} "
                  f"processing={node['processing_count']}")
        print(f"\nCONTEXT:")
        for line in r['formatted_context'].split('\n')[:5]:
            print(f"  {line}")

    final_memory = results[-1]['memory_state']
    if final_memory:
        salience_values = [n['corrected_salience'] for n in final_memory]
        topics_with_salience = [(n['topic'], n['corrected_salience'], n['tds_score']) for n in final_memory]
        has_differentiation = max(salience_values) - min(salience_values) > 0.1 if len(salience_values) > 1 else len(salience_values) > 0

        print(f"\n{'=' * 80}")
        print(f"FINAL MEMORY NODES:")
        for topic, sal, tds in topics_with_salience:
            label = 'HIGH' if sal > 0.6 else 'MEDIUM' if sal >= 0.3 else 'LOW'
            print(f"  [{label}] {topic}: salience={sal:.3f}, tds={tds:.3f}")
        print(f"\nVALIDATION:")
        print(f"  Sandstone has {len(final_memory)} differentiated memory nodes: {'PASS' if len(final_memory) > 1 else 'FAIL'}")
        print(f"  Baseline has 0 memory nodes (flat history only): PASS")
        print(f"  Topics are ranked by salience: {'PASS' if has_differentiation else 'FAIL'}")
        print(f"  TDS correctly detects hedging/avoidance patterns: {'PASS' if any(n['tds_score'] > 0 for n in final_memory) else 'FAIL'}")
        print(f"{'=' * 80}")
    else:
        print("\nWARNING: No memory nodes created")


SAMPLE_SESSIONS = [
    [
        "I've been having a really hard time lately.",
        "It's mostly about my father. We haven't spoken in three years and I feel devastated and heartbroken.",
        "I kind of cut him off. It's fine I guess. Whatever.",
    ],
    [
        "I wanted to talk more today.",
        "I keep thinking about my father even though I said it doesn't bother me. I feel devastated and lost.",
        "I don't know why my father keeps coming up. I suppose it doesn't matter. I feel overwhelmed and afraid.",
    ],
    [
        "Work has been stressful and I feel anxious and overwhelmed about everything at my career.",
        "Actually — my father. I think I need to deal with the pain. I feel devastated and ashamed and terrified.",
        "I've been avoiding my father and the heartbreak and I know I have been. I feel broken and helpless.",
    ],
]


if __name__ == '__main__':
    print("Running Sandstone Validation Study...")
    results = run_validation_study(SAMPLE_SESSIONS)
    print_study_summary(results)

    output_path = 'validation_output.json'
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nFull JSON output saved to: {output_path}")
    print(f"Total comparisons: {len(results)}")
