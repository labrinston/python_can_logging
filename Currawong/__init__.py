"""
Currawong CAN ICD Package
=========================

This package provides a high-level interface for interacting with
Currawong can2pwm devices via the python-can library.

Example Usage:
-------------
import can
from Currawong import discover_devices, make_message, PWMCommandPacket, CSVListener

# Discover devices
bus = can.interface.Bus(bustype='pcan', channel='PCAN_USBBUS1', bitrate=500000)
devices = discover_devices(bus)
if not devices:
    exit()

# Send a command
node_id = devices[0][1]
command = PWMCommandPacket(pwm=1500)
message = make_message(command, node_id)
bus.send(message)

"""

# --- High-level API functions ---
from .api import discover_devices, make_message

# --- Listener classes ---
from .listeners import CSVListener

# --- Packet classes for command and configuration ---
from .packets import (
    MultiCommandPacket,
    PWMCommandPacket,
    TelemetrySettingsPacket,
    setNodeIDPacket,
    serialNumberPacket,
    statusAPacket,
    statusBPacket,
)

# --- Enums for configuration and type-hinting ---
from .enums import (
    deviceType,
    feedbackModes,
    inputModes,
    messageTypes,
)

# --- Expose a version number ---
__version__ = "1.0.0"

