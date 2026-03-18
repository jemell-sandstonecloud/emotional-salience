"""Tests for Sandstone decay engine."""

import os
import sys
import math
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.decay import (
    calculate_decay_rate, calculate_salience_at_time,
    apply_spike, decay_spike, parse_timestamp,
)
import config


class TestDecayRate(unittest.TestCase):
    def test_base_rate(self):
        rate = calculate_decay_rate(0)
        self.assertEqual(rate, config.BASE_DECAY_RATE)

    def test_processed_once(self):
        rate = calculate_decay_rate(1)
        expected = config.BASE_DECAY_RATE * (1 + 1 * config.PROCESSING_BOOST)
        self.assertAlmostEqual(rate, expected)

    def test_processed_five_times(self):
        rate = calculate_decay_rate(5)
        expected = config.BASE_DECAY_RATE * (1 + 5 * config.PROCESSING_BOOST)
        self.assertAlmostEqual(rate, expected)

    def test_monotonic_increase(self):
        rates = [calculate_decay_rate(i) for i in range(10)]
        for i in range(1, len(rates)):
            self.assertGreater(rates[i], rates[i - 1])


class TestSalienceCalculation(unittest.TestCase):
    def test_no_decay_at_zero(self):
        s = calculate_salience_at_time(0.8, 0, 0.01)
        self.assertAlmostEqual(s, 0.8, places=3)

    def test_decay_over_time(self):
        s0 = calculate_salience_at_time(0.8, 0, 0.01)
        s30 = calculate_salience_at_time(0.8, 30, 0.01)
        self.assertGreater(s0, s30)

    def test_floor_at_min(self):
        s = calculate_salience_at_time(0.8, 10000, 0.01)
        self.assertAlmostEqual(s, config.MIN_SALIENCE, places=3)

    def test_processed_decays_faster(self):
        rate_unprocessed = calculate_decay_rate(0)
        rate_processed = calculate_decay_rate(3)
        s_unprocessed = calculate_salience_at_time(0.8, 30, rate_unprocessed)
        s_processed = calculate_salience_at_time(0.8, 30, rate_processed)
        self.assertGreater(s_unprocessed, s_processed)


class TestSpike(unittest.TestCase):
    def test_apply_spike(self):
        node = {'spike_coefficient': 0.0}
        new_spike = apply_spike(node)
        self.assertGreater(new_spike, 0)

    def test_spike_cap(self):
        node = {'spike_coefficient': 0.45}
        new_spike = apply_spike(node, cap=0.5)
        self.assertLessEqual(new_spike, 0.5)

    def test_spike_decay(self):
        decayed = decay_spike(0.3, 3, half_life=3)
        self.assertLess(decayed, 0.3)


class TestParseTimestamp(unittest.TestCase):
    def test_iso_format(self):
        ts = "2024-01-15T10:30:00"
        result = parse_timestamp(ts)
        self.assertIsInstance(result, datetime)

    def test_datetime_passthrough(self):
        now = datetime.utcnow()
        self.assertEqual(parse_timestamp(now), now)

    def test_pg_format(self):
        ts = "2024-01-15 10:30:00"
        result = parse_timestamp(ts)
        self.assertIsInstance(result, datetime)


if __name__ == '__main__':
    unittest.main()
