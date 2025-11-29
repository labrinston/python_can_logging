#!/usr/bin/env python3

from can import Message
import dataclasses
from dataclasses import dataclass
from enum import Enum

# Currawong Message format:
#
# +---------+--------------+-------------+----------------+
# | 0x00    | 0x00         | 0x00        | 0x00           |
# | GroupID | Message Type | Device Type | Device Address |
# | 5 bits  | 8 bits       | 8 bits      | 8 bits         |
# +---------+--------------+-------------+----------------+

GROUP_ID_SHIFT = 24
GROUP_ID_MASK = 0xFF000000
MESSAGE_TYPE_SHIFT = 16
MESSAGE_TYPE_MSK = 0x00FF0000
DEVICE_TYPE_SHIFT = 8
DEVICE_ADDRESS_MASK = 0xFF
 # --- Helpers --- #

# -- Bits
def get_bit(field: int, bit_position: int) -> int:
    return (field >> bit_position) & 0x1

def set_bit(field: int, bit_position: int) -> int:
    """Set specific bits in a field to a value."""
    mask = (1 << bit_position)
    return (field & ~mask) | mask

def clear_bit(field: int, bit_position: int) -> int:
    """Set specific bits in a field to a value."""
    mask = (0 << bit_postion)
    return field & (0 << bit_position)

def get_bits(field: int, mask: int, shift: int) -> int:
    return (field & mask) >> shift

def set_bits(field: int, value: int, mask: int, shift: int) -> int:
    """Set specific bits in a field to a value."""
    return (field & ~mask) | ((value << shift) & mask)

class can2pwm():

    DEVICE_TYPE = 0x0A 
    # --- Enums --- #

    class deviceType(Enum):
        SERVO = 0x00
        CAN2PWM = 0x0A

    class inputModes(Enum):
        STANDBY = 0
        PWM = 1
        RPM = 2

    class feedbackModes(Enum):
        NONE = 0
        RPM = 1
        PULSE_WIDTH = 2
        DUTY_CYCLE = 3
        ANALOG = 4

    class messageTypes(Enum):
        MULTI_COMMAND = 0x00
        PWM_COMMAND = 0x10
        HOME_COMMAND = 0x15
        DISABLE_PACKET = 0x20
    @dataclass
    class PacketBase:
        """Base class for Currawong CANbus data packets"""

        MESSAGE_TYPE = None
        
        def to_bytes(self) -> bytearray:
            """Converts to wire format from dataclass fields."""

        @classmethod
        def from_bytes(cls, data: bytes):
            """Converts to dataclass fields from wire format."""
        
        # Does it make sense to do this here?
        @classmethod
        def csv_header(cls, fields=None):
            print(f"Creating csv headers for: {fields}")
            if fields is None:
                return [f.name for f in dataclasses.fields(cls)]
            else:
                # Should probably validate the fields so we can fail at header construction instead of on data retrival
                return fields

        def to_csv(self, fields=None):
            if fields is None:
                # This should convert things to a string
                # for f in dataclasses.fields(self): 
                return [f"{getattr(self, f.name)}" for f in dataclasses.fields(self)]
            else:
                return [f"{getattr(self, field)}" for field in fields]

        # def to_csv_row(self, include_timestamp=True):

        #     if self.LOG_FIELDS is None:
        #         fields = [v for k, v in self.__dict__.items() if not k.startswith('_')]
        #     else:
        #         fields = [getattr(self, field) for field in self.LOG_FIELDS]
        #     return fields

        # @classmethod
        # def csv_header(cls):
        #     """Return CSV header as a list"""

        #     if cls.LOG_FIELDS is None:
        #         # Get all fields            
        #         fields = [ f.name for f in dataclasses.fields(cls) ]
        #     else:
        #         fields = cls.LOG_FIELDS

        #     return fields

        # If we want to return a string instead?
        # def to_csv_string(self):
        
    @dataclass
    class MultiCommandPacket:
        """"""

        commandA: int # 0..1 I16
        commandB: int # 2..3 I16
        commandC: int # 3..4 I16
        commandD: int # 4..5 I16

        MESSAGE_TYPE = 0x00
        INPUT_LIM_POS = 20000
        INPUT_LIM_NEG = -20000

        def __init__(self, offset, commandA, commandB, commandC, commandD):

            if not self.INPUT_LIM_NEG > commandA > self.INPUT_LIM_POS:
                raise ValueError(f"commandA out of range: {commandA}. Min: {self.INPUT_LIM_NEG} Max: {self.INPUT_LIM_POS}")
            if not self.INPUT_LIM_NEG > commandB > self.INPUT_LIM_POS:
                raise ValueError(f"commandB out of range: {commandB}. Min: {self.INPUT_LIM_NEG} Max: {self.INPUT_LIM_POS}")
            if not self.INPUT_LIM_NEG > commandC > self.INPUT_LIM_POS:
                raise ValueError(f"commandC out of range: {commandC}. Min: {self.INPUT_LIM_NEG} Max: {self.INPUT_LIM_POS}")
            if not self.INPUT_LIM_NEG > commandD > self.INPUT_LIM_POS:
                raise ValueError(f"commandD out of range: {commandD}. Min: {self.INPUT_LIM_NEG} Max: {self.INPUT_LIM_POS}")

            self.commandA = commandA
            self.commandB = commandB
            self.commandC = commandC
            self.commandD = commandD

        def to_can_bytes(self):
            return bytearray([
                *self.commandA.to_bytes(1, 'big', signed=True),
                *self.commandB.to_bytes(1, 'big', signed=True),
                *self.commandC.to_bytes(1, 'big', signed=True),
                *self.commandD.to_bytes(1, 'big', signed=True)
            ])
