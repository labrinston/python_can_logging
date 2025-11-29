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

    def test_setNodeID(self):

        # Test values
        test_cmd = 0x50
        test_serial = 0x174 # 371 in decimal
        test_nodeID = 0x30 # 48 in decimal

        # Values under test
        original = icd.setNodeIDPacket(serialNumber = test_serial, nodeID = test_nodeID)
        encoded  = original.to_can_bytes()
        decoded  = icd.setNodeIDPacket.from_can_bytes(encoded)

        print(f"Encoded: {encoded}")
        print(f"Decoded: {decoded}")
        # Expectations
        expected_encoded = bytearray([0x50, 0x00, 0x00, 0x01, 0x74, 0x30])

        # Test the encode
        self.assertEqual(encoded, expected_encoded,
                         f"\nExpected: {expected_encoded}\nGot: {encoded}")

        # Test the decode
        self.assertEqual(decoded.serialNumber, test_serial,
                         f"\nExpected: {test_serial:04X}\nGot: {decoded.serialNumber:04X}")
        
        self.assertEqual(decoded.nodeID, test_nodeID,
                         f"\nExpected: {test_nodeID:04X}\nGot: {decoded.nodeID:04X}")
        
        self.assertEqual(decoded.command, test_cmd,                        
                         f"\nExpected: {test_cmd:04X}\nGot: {decoded.command:04X}")

    def test_TelemetrySettingsPacket(self):
        # Test values
        test_period  = 50
        test_silence = 50
        test_statusA = True
        test_statusB = True
        test_packets = 0xC0

        # Expected values
        # 50ms per bit => 0x01 for period & silence
        # statusA & statusB enabled => 8 + 4 = 12 = 0xC0
        expected_encoded = bytearray([0x01, 0x01, 0xC0])

        original = icd.TelemetrySettingsPacket(test_period, test_silence,
                                               test_statusA, test_statusB)
        encoded = original.to_can_bytes()
        decoded = icd.TelemetrySettingsPacket.from_can_bytes(encoded)

        # Test the encode
        self.assertEqual(encoded, expected_encoded)
        self.assertEqual(decoded.period, test_period)
        self.assertEqual(decoded.silence, test_silence)
        self.assertEqual(decoded.statusA, True)
        self.assertEqual(decoded.statusB, True)

if __name__ == '__main__':
    unittest.main()
