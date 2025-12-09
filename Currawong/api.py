#!/usr/bin/env python3

import time
from can import Message, CanError
from .packets import serialNumberPacket
from .enums import deviceType, messageTypes

# --- CAN ID Constants --- #
GROUP_ID = 0x07
DEVICE_TYPE_CAN2PWM = deviceType.CAN2PWM.value

def make_message(packet, nodeID: int) -> Message:
    """
    Constructs a python-can Message from a packet dataclass and a node ID.

    Args:
        packet: An instance of a packet class (e.g., PWMCommandPacket).
        nodeID: The destination device's node ID (0-255).

    Returns:
        A python-can Message object ready to be sent.
    """
    can_id = (
        (GROUP_ID << 24)
        | (packet.message_type << 16)
        | (DEVICE_TYPE_CAN2PWM << 8)
        | nodeID
    )
    message = Message(arbitration_id=can_id, data=packet.to_bytes())
    return message


def discover_devices(bus) -> list[tuple[int, int]]:
    """
    Discovers Currawong can2pwm devices on the bus.

    Sends a broadcast request for serial numbers and listens for responses.

    Args:
        bus: An active python-can Bus instance.

    Returns:
        A list of tuples, where each tuple is (serial_number, node_id).
    """
    # Setup broadcast of a serialNumberPacket request
    broadcast_id = 0xFF
    msg_type = messageTypes.MULTI_COMMAND.value # This should be a generic request type
    
    can_id_base = (
        (GROUP_ID << 24) | (msg_type << 16) | (DEVICE_TYPE_CAN2PWM << 8)
    )
    can_id = can_id_base | broadcast_id
    
    # A request for a serial number is an empty message
    msg = Message(arbitration_id=can_id, is_extended_id=True, data=[])

    try:
        bus.send(msg)
    except CanError as e:
        print(f"Error sending discovery message: {e}")
        return []

    # Listen for responses
    seen_serials = set()
    devices_found = []
    start_time = time.time()
    while time.time() - start_time < 2:  # Listen for 2 seconds
        rx_msg = bus.recv(timeout=0.1)
        if rx_msg is None:
            continue

        # Check if the response is a serial number packet from a can2pwm device
        msg_type = (rx_msg.arbitration_id >> 16) & 0xFF
        dev_type = (rx_msg.arbitration_id >> 8) & 0xFF
        node_id = rx_msg.arbitration_id & 0xFF

        if (
            dev_type == DEVICE_TYPE_CAN2PWM
            and msg_type == serialNumberPacket.message_type
            and node_id != 0xFF
        ):
            packet = serialNumberPacket.from_bytes(rx_msg.data)
            if packet and packet.serialNumber not in seen_serials:
                seen_serials.add(packet.serialNumber)
                devices_found.append((packet.serialNumber, node_id))

    if not devices_found:
        print(f"No can2pwm devices responded to broadcast on ID {can_id:X}")

    return devices_found