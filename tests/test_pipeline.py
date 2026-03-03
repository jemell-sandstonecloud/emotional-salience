"""Full Pipeline Test — 3-session simulation validating all mechanisms."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DATABASE_PATH'] = 'db/sandstone_test_pipeline.db'

from db.database import (
    init_db, reset_connection, get_nodes_by_user, get_node_by_topic,
    mark_processed, insert_session, insert_message, insert_node, update_corrected_salience
)
from core.ingestion import process_message
from core.decay import calculate_decay_rate, calculate_salience_at_time, run_decay_update
from core.retrieval import format_context, get_context_summary, get_session_context
from api.routes import get_sandstone_response, get_baseline_response
import config


class TestFullPipeline(unittest.TestCase):
    def setUp(self):
        reset_connection()
        try:
            os.remove('db/sandstone_test_pipeline.db')
        except FileNotFoundError:
            pass
        init_db()
        self.user_id = 'pipeline_test_user'

    def test_three_session_simulation(self):
        session1_msgs = [
            "I've been having a really hard time lately.",
            "It's mostly about my father. We haven't spoken in three years and I feel devastated and heartbroken.",
            "I feel so much grief and loss about the whole situation with my father."
        ]

        session_acc = []
        for msg in session1_msgs:
            session_acc.append(msg)
            process_message(self.user_id, msg, session_acc)

        nodes_s1 = get_nodes_by_user(self.user_id)
        self.assertGreater(len(nodes_s1), 0)

        topics_s1 = [n['topic'] for n in nodes_s1]
        has_family_topic = any(t in topics_s1 for t in ['father', 'grief', 'loss'])
        self.assertTrue(has_family_topic)

        session2_msgs = [
            "I wanted to talk more today.",
            "I keep thinking about my father even though I said it doesn't matter I guess maybe it's fine whatever.",
            "I don't know why the grief keeps coming up. I suppose it's not that bad, I kind of feel lost.",
        ]

        session_acc = []
        for msg in session2_msgs:
            session_acc.append(msg)
            process_message(self.user_id, msg, session_acc)

        nodes_s2 = get_nodes_by_user(self.user_id)
        topic_counts = {}
        for n in nodes_s2:
            topic_counts[n['topic']] = topic_counts.get(n['topic'], 0) + 1
        for topic, count in topic_counts.items():
            self.assertEqual(count, 1)

        session3_msgs = [
            "Work has been really stressful and I feel overwhelmed and anxious about everything.",
            "Actually — the grief about my father. I think I need to deal with it and I feel devastated.",
            "I've been avoiding the pain and I know I have been. I feel ashamed and lost.",
        ]

        session_acc = []
        for msg in session3_msgs:
            session_acc.append(msg)
            process_message(self.user_id, msg, session_acc)

        nodes_s3 = get_nodes_by_user(self.user_id)
        self.assertGreater(len(nodes_s3), 0)

    def test_processing_increases_decay(self):
        msg = "I feel devastated and heartbroken about the grief of losing my father after years of painful silence"
        process_message(self.user_id, msg, [msg])

        nodes = get_nodes_by_user(self.user_id)
        self.assertGreater(len(nodes), 0)
        node = nodes[0]
        original_rate = node['decay_rate']

        for _ in range(5):
            mark_processed(node['id'])

        run_decay_update()

        updated_node = get_nodes_by_user(self.user_id)[0]
        self.assertGreater(updated_node['decay_rate'], original_rate)

    def test_core_claim_14_day_simulation(self):
        base_score = 0.8
        days = 14
        unprocessed_rate = calculate_decay_rate(0)
        unprocessed_s = calculate_salience_at_time(base_score, days, unprocessed_rate)
        processed_rate = calculate_decay_rate(10)
        processed_s = calculate_salience_at_time(base_score, days, processed_rate)
        self.assertLess(processed_s, unprocessed_s * 0.5)

    def test_context_formatting(self):
        high_id = insert_node(self.user_id, 'grief', 'Deep grief disclosure',
            {'sdv': 0.8, 'cscv': 1.0, 'aahs': 0.9, 'swv': 0.7, 'pdv': 0.5}, 0.78)
        update_corrected_salience(high_id, 0.82)

        med_id = insert_node(self.user_id, 'work', 'Work stress',
            {'sdv': 0.4, 'cscv': 1.0, 'aahs': 0.5, 'swv': 0.3, 'pdv': 0.2}, 0.48)
        update_corrected_salience(med_id, 0.45)

        low_id = insert_node(self.user_id, 'health', 'Minor health concern',
            {'sdv': 0.2, 'cscv': 1.0, 'aahs': 0.6, 'swv': 0.1, 'pdv': 0.1}, 0.28)
        update_corrected_salience(low_id, 0.18)

        nodes = get_nodes_by_user(self.user_id)
        context = format_context(nodes)

        self.assertIn('HIGH SALIENCE', context)
        self.assertIn('MEDIUM SALIENCE', context)
        self.assertIn('LOW SALIENCE', context)
        self.assertIn('GRIEF', context)
        self.assertIn('[END CONTEXT]', context)

    def test_sandstone_vs_baseline(self):
        msg = "I feel devastated about losing my father"
        history = [{'role': 'user', 'content': 'I have been struggling lately'}]

        sandstone = get_sandstone_response(self.user_id, msg, history)
        self.assertIsInstance(sandstone, str)
        self.assertGreater(len(sandstone), 0)

        baseline = get_baseline_response(msg, history, flat_summary="User mentioned father issues")
        self.assertIsInstance(baseline, str)
        self.assertGreater(len(baseline), 0)

    def tearDown(self):
        reset_connection()
        try:
            os.remove('db/sandstone_test_pipeline.db')
        except FileNotFoundError:
            pass


if __name__ == '__main__':
    unittest.main()
