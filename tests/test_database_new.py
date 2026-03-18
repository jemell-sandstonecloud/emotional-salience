"""Tests for Sandstone database layer (PostgreSQL)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import SandstoneTestCase
from db.database import (
    insert_node, get_node_by_topic, get_nodes_by_user, update_node,
    insert_study_participant, get_study_participant, get_study_participant_by_email,
    _hash_password, _verify_password,
    insert_conversation_turn, get_conversation_history, get_latest_session_number,
    insert_rating, get_ratings_by_user,
)


class TestMemoryNodes(SandstoneTestCase):
    def test_insert_and_retrieve(self):
        scores = {'sdv': 0.5, 'cscv': 0.3, 'lcs': 0.4, 'swv': 0.2, 'pdv': 0.1}
        node_id = insert_node("user1", "grief", "Lost my father", scores, 0.7)
        node = get_node_by_topic("user1", "grief")
        self.assertIsNotNone(node)
        self.assertEqual(node['topic'], 'grief')
        self.assertAlmostEqual(node['base_score'], 0.7, places=2)

    def test_get_nodes_by_user_ordered(self):
        scores = {'sdv': 0.5, 'cscv': 0.3, 'lcs': 0.4, 'swv': 0.2, 'pdv': 0.1}
        insert_node("user2", "grief", "Lost father", scores, 0.9)
        insert_node("user2", "anxiety", "Work stress", scores, 0.3)
        nodes = get_nodes_by_user("user2")
        self.assertEqual(len(nodes), 2)
        self.assertGreaterEqual(nodes[0]['corrected_salience'], nodes[1]['corrected_salience'])

    def test_update_node(self):
        scores = {'sdv': 0.5, 'cscv': 0.3, 'lcs': 0.4, 'swv': 0.2, 'pdv': 0.1}
        node_id = insert_node("user3", "grief", "Original", scores, 0.5)
        new_scores = {'sdv': 0.8, 'cscv': 0.7, 'lcs': 0.6, 'swv': 0.5, 'pdv': 0.4}
        update_node(node_id, "Updated content", new_scores, 0.9)
        node = get_node_by_topic("user3", "grief")
        self.assertAlmostEqual(node['base_score'], 0.9, places=2)


class TestStudyParticipants(SandstoneTestCase):
    def test_create_and_retrieve(self):
        insert_study_participant("uid1", "test@example.com", "Test User", "A", "password123")
        p = get_study_participant("uid1")
        self.assertIsNotNone(p)
        self.assertEqual(p['email'], 'test@example.com')

    def test_lookup_by_email(self):
        insert_study_participant("uid2", "lookup@example.com", "Lookup", "B", "pass")
        p = get_study_participant_by_email("lookup@example.com")
        self.assertIsNotNone(p)
        self.assertEqual(p['user_id'], 'uid2')

    def test_password_verification(self):
        pw = "securePassword123"
        hashed = _hash_password(pw)
        self.assertTrue(_verify_password(pw, hashed))
        self.assertFalse(_verify_password("wrong", hashed))


class TestConversationHistory(SandstoneTestCase):
    def test_insert_and_retrieve(self):
        insert_conversation_turn("user1", 1, "sandstone", "user", "Hello", 1)
        insert_conversation_turn("user1", 1, "sandstone", "assistant", "Hi there", 1)
        history = get_conversation_history("user1", 1, "sandstone")
        self.assertEqual(len(history), 2)

    def test_latest_session_number(self):
        self.assertEqual(get_latest_session_number("user_new"), 0)
        insert_conversation_turn("user_new", 3, "baseline", "user", "Test", 1)
        self.assertEqual(get_latest_session_number("user_new"), 3)


class TestRatings(SandstoneTestCase):
    def test_insert_and_retrieve(self):
        rating_id = insert_rating(
            "user1", 1, 1, "Hello", "Resp A", "Resp B",
            5, 4, 6, 3, 5, 4, "A", "A"
        )
        ratings = get_ratings_by_user("user1")
        self.assertEqual(len(ratings), 1)
        self.assertEqual(ratings[0]['preference'], 'A')


if __name__ == '__main__':
    unittest.main()
