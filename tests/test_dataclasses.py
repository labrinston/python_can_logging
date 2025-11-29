#!/usr/bin/env python3

import unittest
from Currawong.can2pwm_icd import can2pwm as icd

class TestDataclasses(unittest.TestCase):

    def test_sanity_check(self):
        """Sanity check."""
        # self.assertEqual(0, 1)
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
