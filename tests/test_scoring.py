"""Tests for scoring module — all known bugs must be confirmed fixed."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DATABASE_PATH'] = 'db/sandstone_test_scoring.db'

from core.scoring import (
    calculate_sdv, calculate_cscv, calculate_aahs, calculate_swv,
    calculate_pdv, calculate_base_score, score_message,
    count_emotional_words, count_hedging_phrases
)
from db.database import init_db, reset_connection


class TestSDV(unittest.TestCase):
    def test_short_message_not_max(self):
        score = calculate_sdv("I'm sad", 0, 1)
        self.assertLess(score, 1.0)

    def test_short_below_threshold(self):
        score = calculate_sdv("I'm fine today", 0, 1)
        self.assertEqual(score, 0.0)

    def test_meaningful_disclosure(self):
        msg = "I feel so devastated and heartbroken about losing my father after all these years"
        score = calculate_sdv(msg, 0, 5)
        self.assertGreater(score, 0.0)

    def test_no_emotional_words(self):
        score = calculate_sdv("The weather is nice today and I went to the store for groceries", 0, 1)
        self.assertEqual(score, 0.0)


class TestCSCV(unittest.TestCase):
    def setUp(self):
        reset_connection()
        os.environ['DATABASE_PATH'] = 'db/sandstone_test_scoring.db'
        try:
            os.remove('db/sandstone_test_scoring.db')
        except FileNotFoundError:
            pass
        init_db()

    def test_no_history_returns_one(self):
        score = calculate_cscv('grief', 'new_user', 'I lost my father')
        self.assertEqual(score, 1.0)

    def tearDown(self):
        reset_connection()
        try:
            os.remove('db/sandstone_test_scoring.db')
        except FileNotFoundError:
            pass


class TestAAHS(unittest.TestCase):
    def test_heavily_hedged(self):
        msg = "I guess maybe sort of kind of I suppose it doesn't matter I don't know whatever"
        score = calculate_aahs(msg)
        self.assertLess(score, 0.4, f"Heavily hedged should be < 0.4, got {score}")

    def test_direct_disclosure(self):
        msg = "I am devastated and heartbroken and I need help dealing with this pain"
        score = calculate_aahs(msg)
        self.assertGreater(score, 0.8, f"Direct disclosure should be > 0.8, got {score}")


class TestSWV(unittest.TestCase):
    def test_emotional_message(self):
        msg = "I feel devastated heartbroken terrified and overwhelmed by grief and shame"
        score = calculate_swv(msg)
        self.assertGreater(score, 0.3)

    def test_neutral_message(self):
        msg = "The meeting is at 3pm in conference room B"
        score = calculate_swv(msg)
        self.assertEqual(score, 0.0)


class TestPDV(unittest.TestCase):
    def test_repeated_topic(self):
        msgs = ["My father was never there", "father always left", "thinking about my father"]
        score = calculate_pdv("father", msgs)
        self.assertEqual(score, 1.0)

    def test_no_mentions(self):
        msgs = ["Work is stressful", "I need a break"]
        score = calculate_pdv("father", msgs)
        self.assertEqual(score, 0.0)


class TestBaseScore(unittest.TestCase):
    def test_weights_sum_check(self):
        with self.assertRaises(AssertionError):
            calculate_base_score(0.5, 0.5, 0.5, 0.5, 0.5, weights=[0.1, 0.1, 0.1, 0.1, 0.1])

    def test_valid_weights(self):
        score = calculate_base_score(0.5, 1.0, 0.8, 0.6, 0.3)
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)


class TestScoreMessage(unittest.TestCase):
    def setUp(self):
        reset_connection()
        os.environ['DATABASE_PATH'] = 'db/sandstone_test_scoring2.db'
        try:
            os.remove('db/sandstone_test_scoring2.db')
        except FileNotFoundError:
            pass
        init_db()

    def test_full_score_returns_all_keys(self):
        result = score_message(
            "I feel devastated and terrified about losing my father after all these years of silence",
            'test_user', 'father',
            session_messages=["I feel devastated and terrified about losing my father after all these years of silence"],
            session_position=0, total_session_messages=3
        )
        expected_keys = {'sdv', 'cscv', 'aahs', 'swv', 'pdv', 'base_score'}
        self.assertEqual(set(result.keys()), expected_keys)

    def test_no_dict_mutation(self):
        result = score_message(
            "I feel devastated and terrified about my grief",
            'test_user', 'grief',
            session_messages=[], session_position=0, total_session_messages=1
        )
        base_score = result['base_score']
        scores = {k: v for k, v in result.items() if k != 'base_score'}
        self.assertIn('base_score', result)
        self.assertEqual(len(scores), 5)

    def tearDown(self):
        reset_connection()
        try:
            os.remove('db/sandstone_test_scoring2.db')
        except FileNotFoundError:
            pass


if __name__ == '__main__':
    unittest.main()
