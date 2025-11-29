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
