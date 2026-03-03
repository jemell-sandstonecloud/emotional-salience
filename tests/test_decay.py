"""Tests for decay engine — core patent claim validation."""

import os
import sys
import unittest
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DATABASE_PATH'] = 'db/sandstone_test_decay.db'

from core.decay import (
    calculate_decay_rate, calculate_salience_at_time,
    apply_spike, decay_spike, parse_timestamp, run_decay_update
)
from db.database import init_db, reset_connection, insert_node
import config


class TestDecayRate(unittest.TestCase):
    def test_base_rate_no_processing(self):
        rate = calculate_decay_rate(0)
        self.assertAlmostEqual(rate, 0.01)

    def test_rate_increases_with_processing(self):
        rates = [calculate_decay_rate(i) for i in range(10)]
        for i in range(1, len(rates)):
            self.assertGreater(rates[i], rates[i-1])

    def test_processing_boost_is_0_5(self):
        self.assertEqual(config.PROCESSING_BOOST, 0.5)
        rate = calculate_decay_rate(2)
        self.assertAlmostEqual(rate, 0.02)


class TestSalienceCalculation(unittest.TestCase):
    def test_core_claim_processed_vs_unprocessed(self):
        base_score = 0.8
        days = 14
        unprocessed_rate = calculate_decay_rate(0)
        unprocessed_salience = calculate_salience_at_time(base_score, days, unprocessed_rate)
        processed_rate = calculate_decay_rate(5)
        processed_salience = calculate_salience_at_time(base_score, days, processed_rate)
        diff = unprocessed_salience - processed_salience
        self.assertGreater(diff, 0.15)

    def test_processed_below_50_percent(self):
        base_score = 0.8
        days = 14
        unprocessed_rate = calculate_decay_rate(0)
        unprocessed_salience = calculate_salience_at_time(base_score, days, unprocessed_rate)
        processed_rate = calculate_decay_rate(10)
        processed_salience = calculate_salience_at_time(base_score, days, processed_rate)
        self.assertLess(processed_salience, unprocessed_salience * 0.5)

    def test_salience_floor(self):
        salience = calculate_salience_at_time(0.5, 10000, 1.0)
        self.assertGreaterEqual(salience, config.MIN_SALIENCE)

    def test_spike_increases_salience(self):
        base = 0.5
        days = 7
        rate = 0.01
        without = calculate_salience_at_time(base, days, rate, spike=0.0)
        with_spike = calculate_salience_at_time(base, days, rate, spike=0.2)
        self.assertGreater(with_spike, without)


class TestTimestampParsing(unittest.TestCase):
    def test_iso_format(self):
        dt = parse_timestamp('2025-02-20T10:30:00')
        self.assertEqual(dt.year, 2025)

    def test_sqlite_format(self):
        dt = parse_timestamp('2025-02-20 10:30:00')
        self.assertEqual(dt.year, 2025)

    def test_microseconds(self):
        dt = parse_timestamp('2025-02-20T10:30:00.123456')
        self.assertEqual(dt.year, 2025)


class TestSpike(unittest.TestCase):
    def test_apply_spike(self):
        node = {'spike_coefficient': 0.1}
        new_spike = apply_spike(node, increment=0.15, cap=0.5)
        self.assertEqual(new_spike, 0.25)

    def test_spike_cap(self):
        node = {'spike_coefficient': 0.45}
        new_spike = apply_spike(node, increment=0.15, cap=0.5)
        self.assertEqual(new_spike, 0.5)

    def test_spike_decay(self):
        decayed = decay_spike(0.5, 3, half_life=3)
        self.assertAlmostEqual(decayed, 0.25, places=2)


class TestRunDecayUpdate(unittest.TestCase):
    def setUp(self):
        reset_connection()
        os.environ['DATABASE_PATH'] = 'db/sandstone_test_decay.db'
        try:
            os.remove('db/sandstone_test_decay.db')
        except FileNotFoundError:
            pass
        init_db()

    def test_run_decay_update(self):
        insert_node('user1', 'grief', 'I lost someone',
                     {'sdv': 0.5, 'cscv': 1.0, 'aahs': 0.7, 'swv': 0.6, 'pdv': 0.3}, 0.62)
        count = run_decay_update()
        self.assertEqual(count, 1)

    def tearDown(self):
        reset_connection()
        try:
            os.remove('db/sandstone_test_decay.db')
        except FileNotFoundError:
            pass


if __name__ == '__main__':
    unittest.main()
