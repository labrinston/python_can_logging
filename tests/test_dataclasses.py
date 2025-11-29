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

    def test_serialNumber(self):

        # Test values
        test_hw = 0x01
        test_serial = 0x000174 # 371 in decimal
        test_IDA = 0x02
        test_IDB = 0xFF

        # Values under test
        original = icd.serialNumberPacket(
            hwRev=test_hw,
            serialNumber=test_serial,
            userIDA=test_IDA,
            userIDB=test_IDB)
        encoded  = original.to_can_bytes()
        decoded  = icd.serialNumberPacket.from_can_bytes(encoded)

        # Expectations
        expected_encoded = bytearray([0x01, 0x00, 0x01, 0x74, 0x00, 0x02, 0x00, 0xFF])

        # Test the encode
        self.assertEqual(encoded, expected_encoded,
                         f"\nExpected: {expected_encoded}\nGot: {encoded}")

        # Test the decode
        self.assertEqual(decoded.serialNumber, test_serial,
                         f"\nExpected: {test_serial:04X}\nGot: {decoded.serialNumber:04X}")
        
        self.assertEqual(decoded.userIDA, test_IDA,
                         f"\nExpected: {test_IDA:04X}\nGot: {decoded.userIDA:04X}")
        
        self.assertEqual(decoded.userIDB, test_IDB,                        
                         f"\nExpected: {test_IDB:04X}\nGot: {decoded.userIDB:04X}")
if __name__ == '__main__':
    unittest.main()
