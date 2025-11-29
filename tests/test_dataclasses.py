#!/usr/bin/env python3

import unittest
from Currawong.can2pwm_icd import can2pwm as icd

class TestDataclasses(unittest.TestCase):

    def test_sanity_check(self):
        """Sanity check."""
        # self.assertEqual(0, 1)
        self.assertTrue(True)

    def test_statusB_Positive(self):
        """Tests statusB packet de/encoding with positive current value"""

        test_current = 1500
        test_voltage = 5000
        
        original = icd.statusBPacket(current=test_current, voltage=test_voltage)
        encoded = original.to_can_bytes()
        decoded = icd.statusBPacket.from_can_bytes(encoded)

        self.assertEqual(
            decoded.current,
            test_current
        )

        self.assertEqual(decoded.voltage, test_voltage)

    def test_statusB_Negative(self):
        """Tests statusB packet de/encoding with negative current value"""

        test_current = -1500
        test_voltage = 5000
        
        original = icd.statusBPacket(current=test_current, voltage=test_voltage)
        encoded = original.to_can_bytes()
        decoded = icd.statusBPacket.from_can_bytes(encoded)

        self.assertEqual(decoded.current,
                         test_current,
                         f"""Current mismatch: expected {test_current}mA = 0x{test_current:04X},
                         got: {decoded.current} = 0x{decoded.current:04X}"""
                         )
        self.assertEqual(decoded.voltage, test_voltage)
if __name__ == '__main__':
    unittest.main()
