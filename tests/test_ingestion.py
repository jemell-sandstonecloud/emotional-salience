"""Tests for ingestion module — deduplication, threshold, topic detection."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DATABASE_PATH'] = 'db/sandstone_test_ingestion.db'

from core.ingestion import detect_topics, process_message
from db.database import init_db, reset_connection, get_nodes_by_user, get_node_by_topic


class TestTopicDetection(unittest.TestCase):
    def test_single_topic_not_multiple(self):
        topics = detect_topics("My father and I have a terrible relationship and I feel devastated")
        self.assertEqual(len(topics), 1)

    def test_priority_order(self):
        topics = detect_topics("I feel so much grief and shame about my father leaving")
        self.assertEqual(topics[0], 'grief')

    def test_non_emotional_returns_empty(self):
        topics = detect_topics("The meeting is at 3pm in conference room B")
        self.assertEqual(topics, [])

    def test_emotional_no_specific_topic(self):
        topics = detect_topics("I feel absolutely devastated and terrified about everything happening")
        self.assertEqual(topics, ['general'])


class TestProcessMessage(unittest.TestCase):
    def setUp(self):
        reset_connection()
        os.environ['DATABASE_PATH'] = 'db/sandstone_test_ingestion.db'
        try:
            os.remove('db/sandstone_test_ingestion.db')
        except FileNotFoundError:
            pass
        init_db()

    def test_non_emotional_not_stored(self):
        ids = process_message('user1', 'The weather is nice today', [])
        self.assertEqual(len(ids), 0)
        nodes = get_nodes_by_user('user1')
        self.assertEqual(len(nodes), 0)

    def test_emotional_creates_node(self):
        msg = "I feel devastated and heartbroken about losing my father after years of painful silence and grief"
        ids = process_message('user1', msg, [msg])
        self.assertGreater(len(ids), 0)

    def test_no_duplicate_nodes(self):
        msg1 = "I feel so much grief and loss about my father leaving us when I was young and devastated"
        msg2 = "The grief about my father still haunts me and I feel devastated and heartbroken"
        process_message('user2', msg1, [msg1])
        nodes_after_1 = get_nodes_by_user('user2')
        count_1 = len(nodes_after_1)
        process_message('user2', msg2, [msg1, msg2])
        nodes_after_2 = get_nodes_by_user('user2')
        count_2 = len(nodes_after_2)
        self.assertEqual(count_1, count_2)

    def test_threshold_enforced(self):
        ids = process_message('user3', 'I talked to my father today about lunch', [])
        nodes = get_nodes_by_user('user3')
        self.assertEqual(len(nodes), 0)

    def test_dict_mutation_absent(self):
        msg = "I feel devastated and terrified about losing everything I had and feeling grief"
        process_message('user4', msg, [msg])
        process_message('user4', msg, [msg])

    def tearDown(self):
        reset_connection()
        try:
            os.remove('db/sandstone_test_ingestion.db')
        except FileNotFoundError:
            pass


if __name__ == '__main__':
    unittest.main()
