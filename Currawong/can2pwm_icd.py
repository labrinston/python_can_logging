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

    @dataclass
    class PWMCommandPacket:
        """"""

        pwm: int # 0..1 I16 [us]

        MESSAGE_TYPE = 0x10

        def to_can_bytes(self):
            return bytearray([
                *self.pwm.to_bytes(1, 'big', signed=True)
            ])

        # @classmethod 
        # def from_can_bytes(cls, data):
        #     """"""

    # ----- Eng Commands Packets        ----- #

    # ----- Begin Status Packets      ----- #

    # Message Type - 0x60
    @dataclass
    class statusAPacket(PacketBase):
        """Base structure of the statusA Telemetry Packet"""

        # Message fields (Instance variables)
        status:        int            # 0..1     U16
        inputMode:     'can2pwm.inputModes'     # 0:7..0:5 B3
        feedbackMode:  'can2pwm.feedbackModes'  # 0:4..0:2 B3
        validInput:    bool           # 0:1      B1
        validFeedback: bool           # 0:0      B0
        enabled:       bool           # 1:7      B1
        reserved:      int            # 1:6..1:2 B5
        mapEnabled:    bool           # 1:1      B1
        mapInvalid:    bool           # 1:0      B1
        command:       int            # 2..3     I16
        feedback:      int            # 4..5     U16 Actual PWM value
        pwm:           int            # 6..7     U16 [us]

        # Class Variable
        MESSAGE_TYPE = 0x60
        # Masks & shifts 
        # Status 0..1
        # Byte 0
        INPUT_MODE_MASK = 0xC0    # 0:7..0:5
        INPUT_MODE_SHIFT = 5
        FEEDBACK_MODE_MASK = 0x1B # 0:4..0:2
        FEEDBACK_MODE_SHIFT = 2
        VALID_INPUT_MASK = 0x2    # 0:1
        VALID_INPUT_SHIFT = 1
        VALID_FEEDBACK_MASK = 0x1 # 0:0
        VALID_FEEDBACK_SHIFT = 0
        # Byte 1
        ENABLED_MASK = 0x8000     # 1:7
        ENABLED_SHIFT = 15
        RESERVED_MASK = 0x7C00     # 1:6..1:2
        RESEREVED_SHIFT = 10
        MAP_ENABLED_MASK = 0x200  # 1:1
        MAP_ENABLED_SHIFT = 9
        MAP_INVALID_MASK = 0x100  # 1:0
        MAP_INVALID_SHIFT = 8

        # Telemetry is only received therefore no to_bytes method is needed
        # EXCEPT - if you're polling, in which case data = []

        @classmethod
        def from_can_bytes(cls, data):
            status_value   = int.from_bytes(data[0:2], 'big')
            command_value  = int.from_bytes(data[2:4], 'big')
            feedback_value = int.from_bytes(data[4:6], 'big')
            pwm_value      = int.from_bytes(data[6:8], 'big')
            return cls(
                status         = status_value,
                inputMode      = get_bits(status_value, cls.INPUT_MODE_MASK, cls.INPUT_MODE_SHIFT),
                feedbackMode   = get_bits(status_value, cls.FEEDBACK_MODE_MASK, cls.FEEDBACK_MODE_SHIFT),
                validInput     = bool(get_bit(status_value, 1)),
                validFeedback  = bool(get_bit(status_value, 0)),
                enabled        = bool(get_bit(status_value, 15)),
                reserved       = get_bits(status_value,cls.RESERVED_MASK, 2),
                mapEnabled     = bool(get_bit(status_value, 9)),
                mapInvalid     = bool(get_bit(status_value, 8)),
                command        = command_value,
                feedback       = feedback_value,
                pwm            = pwm_value
            )
