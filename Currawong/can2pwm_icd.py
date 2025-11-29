#!/usr/bin/env python3

from can import Message
import dataclasses
from dataclasses import dataclass

# Currawong Message format:
#
# +---------+--------------+-------------+----------------+
# | 0x00    | 0x00         | 0x00        | 0x00           |
# | GroupID | Message Type | Device Type | Device Address |
# | 5 bits  | 8 bits       | 8 bits      | 8 bits         |
# +---------+--------------+-------------+----------------+

class can2pwm():
