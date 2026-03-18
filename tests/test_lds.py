"""Tests for Sandstone LDS (Therapeutic Depth Score)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.lds import calculate_lds, apply_lds_correction
import config


class TestLDS(unittest.TestCase):
    def test_basic_lds(self):
        nodes = []
        lds = calculate_lds("grief", "I lost my father last year", "user1", nodes)
        self.assertIsInstance(lds, float)
        self.assertGreaterEqual(lds, -1.0)
        self.assertLessEqual(lds, 1.0)

    def test_lds_with_history(self):
        nodes = [
            {'topic': 'grief', 'content': 'My father passed away', 'processing_count': 2,
             'current_salience': 0.7, 'corrected_salience': 0.7, 'base_score': 0.8,
             'lds_score': 0.1, 'id': '1', 'user_id': 'user1'}
        ]
        lds = calculate_lds("grief", "I still think about my father", "user1", nodes)
        self.assertIsInstance(lds, float)


class TestLDSCorrection(unittest.TestCase):
    def test_positive_lds(self):
        corrected = apply_lds_correction(0.5, 0.3)
        self.assertGreater(corrected, 0.5)

    def test_additive_lds(self):
        # LDS is always >= 0, correction is always additive
        corrected = apply_lds_correction(0.5, 0.3)
        self.assertGreater(corrected, 0.5)

    def test_zero_lds(self):
        corrected = apply_lds_correction(0.5, 0.0)
        self.assertAlmostEqual(corrected, 0.5)

    def test_bounds(self):
        corrected = apply_lds_correction(0.99, 0.99)
        self.assertLessEqual(corrected, 1.0)
        corrected = apply_lds_correction(0.01, -0.99)
        self.assertGreaterEqual(corrected, 0.0)


if __name__ == '__main__':
    unittest.main()
