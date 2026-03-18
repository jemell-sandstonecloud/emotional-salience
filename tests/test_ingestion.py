"""Tests for Sandstone ingestion module."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import SandstoneTestCase
from core.ingestion import detect_topics, process_message
from db.database import get_node_by_topic, get_nodes_by_user
import config


class TestDetectTopics(unittest.TestCase):
    def test_grief_topic(self):
        topics = detect_topics("I lost my father to grief last year")
        self.assertIn("grief", topics)

    def test_no_topic(self):
        topics = detect_topics("The weather is nice today")
        self.assertEqual(topics, [])

    def test_priority_ranking(self):
        topics = detect_topics("I experienced trauma and have anxiety about it")
        self.assertEqual(topics, ["trauma"])


class TestProcessMessage(SandstoneTestCase):
    def test_process_emotional_message(self):
        nodes = process_message("user1", "I am devastated and heartbroken about my grief")
        self.assertIsInstance(nodes, list)

    def test_process_non_emotional(self):
        nodes = process_message("user1", "The sky is blue")
        self.assertEqual(nodes, [])

    def test_deduplication(self):
        process_message("user1", "I feel devastated about my grief and loss")
        process_message("user1", "My grief is overwhelming and I feel heartbroken")
        all_nodes = get_nodes_by_user("user1")
        grief_nodes = [n for n in all_nodes if n['topic'] == 'grief']
        self.assertLessEqual(len(grief_nodes), 1)


if __name__ == '__main__':
    unittest.main()
