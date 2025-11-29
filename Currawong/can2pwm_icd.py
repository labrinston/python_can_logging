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
        
