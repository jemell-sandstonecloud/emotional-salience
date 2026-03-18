"""Tests for Sandstone full pipeline integration."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import SandstoneTestCase
from core.ingestion import process_message
from core.decay import run_decay_update, calculate_decay_rate
from db.database import (
    get_nodes_by_user, get_node_by_topic, mark_processed, get_all_nodes,
)
import config


class TestFullPipeline(SandstoneTestCase):
    def test_ingest_and_retrieve(self):
        process_message("pipe_user", "I am devastated and heartbroken about my grief")
        nodes = get_nodes_by_user("pipe_user")
        self.assertGreater(len(nodes), 0)

    def test_ingest_and_decay(self):
        process_message("pipe_user2", "I feel overwhelming grief and loss for my father")
        nodes_before = get_nodes_by_user("pipe_user2")
        if nodes_before:
            initial_salience = nodes_before[0]['current_salience']
            run_decay_update()
            nodes_after = get_nodes_by_user("pipe_user2")
            # Salience should stay same or decrease (just created, so minimal decay)
            self.assertGreaterEqual(initial_salience, nodes_after[0]['current_salience'] - 0.01)

    def test_processing_increases_decay(self):
        process_message("pipe_user3", "I feel devastated and heartbroken about trauma")
        nodes = get_nodes_by_user("pipe_user3")
        if nodes:
            node = nodes[0]
            rate_before = calculate_decay_rate(node['processing_count'])
            mark_processed(node['id'])
            rate_after = calculate_decay_rate(node['processing_count'] + 1)
            self.assertGreater(rate_after, rate_before)

    def test_multiple_users_isolated(self):
        process_message("iso_user1", "I feel grief and devastation about loss")
        process_message("iso_user2", "I feel anxious and scared about work")
        nodes1 = get_nodes_by_user("iso_user1")
        nodes2 = get_nodes_by_user("iso_user2")
        user1_ids = {n['user_id'] for n in nodes1}
        user2_ids = {n['user_id'] for n in nodes2}
        self.assertTrue(user1_ids.issubset({"iso_user1"}))
        self.assertTrue(user2_ids.issubset({"iso_user2"}))


if __name__ == '__main__':
    unittest.main()
