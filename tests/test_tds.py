"""Tests for TDS module — ACD product formula and NCS new-user fix."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DATABASE_PATH'] = 'db/sandstone_test_tds.db'

from core.tds import (
    calculate_acd, calculate_ncs, calculate_tds, apply_tds_correction, calculate_ssi, calculate_ccm
)
from db.database import init_db, reset_connection


class TestACD(unittest.TestCase):
    def test_congruent_lower_than_divergent(self):
        congruent = "I feel devastated and terrified"
        divergent = "I kind of feel devastated I guess maybe"
        acd_congruent = calculate_acd(congruent)
        acd_divergent = calculate_acd(divergent)
        self.assertLess(acd_congruent, acd_divergent)

    def test_high_emotion_no_hedging_low(self):
        msg = "I am devastated and heartbroken and terrified"
        acd = calculate_acd(msg)
        self.assertLess(acd, 0.2)

    def test_high_emotion_heavy_hedging_high(self):
        msg = "I guess I kind of feel devastated I suppose maybe it's sort of terrifying I don't know whatever"
        acd = calculate_acd(msg)
        self.assertGreater(acd, 0.1)

    def test_no_emotion_no_hedging(self):
        msg = "The weather is nice today"
        acd = calculate_acd(msg)
        self.assertLess(acd, 0.1)


class TestNCS(unittest.TestCase):
    def setUp(self):
        reset_connection()
        os.environ['DATABASE_PATH'] = 'db/sandstone_test_tds.db'
        try:
            os.remove('db/sandstone_test_tds.db')
        except FileNotFoundError:
            pass
        init_db()

    def test_new_user_returns_one(self):
        ncs = calculate_ncs('grief', 'I lost my father', 'brand_new_user')
        self.assertEqual(ncs, 1.0)

    def tearDown(self):
        reset_connection()
        try:
            os.remove('db/sandstone_test_tds.db')
        except FileNotFoundError:
            pass


class TestSSI(unittest.TestCase):
    def test_ssi_returns_zero(self):
        self.assertEqual(calculate_ssi(), 0.0)


class TestTDS(unittest.TestCase):
    def setUp(self):
        reset_connection()
        os.environ['DATABASE_PATH'] = 'db/sandstone_test_tds2.db'
        try:
            os.remove('db/sandstone_test_tds2.db')
        except FileNotFoundError:
            pass
        init_db()

    def test_first_session_tds_low(self):
        tds = calculate_tds('grief', 'I am devastated about losing my father', 'new_user')
        self.assertLess(tds, 0.15)

    def test_tds_range(self):
        tds = calculate_tds('grief', 'I feel devastated I guess maybe', 'new_user')
        self.assertGreaterEqual(tds, 0.0)
        self.assertLessEqual(tds, 1.0)

    def tearDown(self):
        reset_connection()
        try:
            os.remove('db/sandstone_test_tds2.db')
        except FileNotFoundError:
            pass


class TestTDSCorrection(unittest.TestCase):
    def test_high_tds_reduces_salience(self):
        original = 0.8
        corrected = apply_tds_correction(original, 0.9)
        self.assertLess(corrected, original)

    def test_low_tds_preserves_salience(self):
        original = 0.8
        corrected = apply_tds_correction(original, 0.05)
        self.assertGreater(corrected, original * 0.95)

    def test_correction_floor(self):
        corrected = apply_tds_correction(0.01, 1.0)
        self.assertGreaterEqual(corrected, 0.01)


if __name__ == '__main__':
    unittest.main()
