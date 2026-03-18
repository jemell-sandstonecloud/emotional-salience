"""Tests for Sandstone scoring module."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.scoring import score_message, count_emotional_words
import config


class TestCountEmotionalWords(unittest.TestCase):
    def test_positive_words(self):
        self.assertGreater(count_emotional_words("I feel grateful and hopeful"), 0)

    def test_negative_words(self):
        self.assertGreater(count_emotional_words("I am devastated and heartbroken"), 0)

    def test_no_emotional_words(self):
        self.assertEqual(count_emotional_words("The weather is sunny today"), 0)

    def test_mixed_words(self):
        count = count_emotional_words("I feel both hopeful and anxious about the future")
        self.assertGreaterEqual(count, 2)


class TestScoreMessage(unittest.TestCase):
    def test_high_emotional_score(self):
        result = score_message(
            "I am absolutely devastated and heartbroken about losing my father",
            "user1", "grief"
        )
        self.assertIn('base_score', result)
        self.assertGreater(result['base_score'], 0.3)

    def test_low_emotional_score(self):
        result = score_message(
            "The sky is blue today",
            "user1", "weather"
        )
        self.assertIn('base_score', result)
        self.assertLess(result['base_score'], 0.3)

    def test_all_five_signals(self):
        result = score_message(
            "I feel so ashamed and guilty about what happened with my mother",
            "user1", "shame"
        )
        for key in ['sdv', 'cscv', 'lcs', 'swv', 'pdv']:
            self.assertIn(key, result)
            self.assertGreaterEqual(result[key], 0.0)
            self.assertLessEqual(result[key], 1.0)

    def test_weights_sum(self):
        self.assertAlmostEqual(sum(config.DEFAULT_WEIGHTS), 1.0, places=5)


class TestScoringEdgeCases(unittest.TestCase):
    def test_empty_message(self):
        result = score_message("", "user1", "test")
        self.assertIn('base_score', result)

    def test_very_long_message(self):
        msg = "I feel devastated " * 100
        result = score_message(msg, "user1", "grief")
        self.assertIn('base_score', result)
        self.assertLessEqual(result['base_score'], 1.0)


if __name__ == '__main__':
    unittest.main()
