#!/usr/bin/env python3

import can
import time
from Currawong.can2pwm_icd import can2pwm

# ---- Bus Setup ---- #

# Setup the bus
# Linux
bus = can.Bus(channel = 'can0', interface='socketcan')
# Windows
# bus = can.Bus(channel = '?', interface='pcan') # TODO channel param for windows

# ---- Find Currawong Devices ---- #

dev_tuple = can2pwm.discover_devices(bus)
print(f"Found: {dev_tuple}")

# ---- Set NodeIDs ---- #

new_ids = [ 0x23, 0x44 ]
for serial_num, curr_id in dev_tuple:
    for new_id in new_ids:
        packet = can2pwm.setNodeIDPacket(serial_num, new_id)
        message = can2pwm.make_message(packet, curr_id)
        print(f"setNodeID: {message}")
        bus.send(message)

# ---- Enable Telemetry ---- #

# Enable statusA and statusB
telem_packet = can2pwm.TelemetrySettingsPacket(period=100, silence=100, 
                                  packets=0, statusA=True, 
                                  statusB=True)
# Create a broadcast message - 0xFF
telem_message = can2pwm.make_message(telem_packet, 0xFF)
print(f"{telem_message}")
bus.send(telem_message)
       
# ---- Listener Setup ---- #

# Create logging config (Note: this only applies to the can2pwm CSVListener)
log_config = {
    'statusAPacket': can2pwm.PacketLogConfig(enabled=True, fields=['feedback', 'command']),
    'statusBPacket': can2pwm.PacketLogConfig(enabled=True, fields=['current', 'voltage'])
}

# Request listeners from the can2pwm module
print_listener = can2pwm.PrintListener()
csv_listener = can2pwm.CSVListener(log_dir="./", log_config=log_config)

# Provide the csv_listener to the notifier
# Reception and logging of CAN messages will be handled by a separate thread
notifier = can.Notifier(bus, [csv_listener])

# ------------------- #

# TODO Example transmission code

time.sleep(2)

# 1. Issue full retraction - 900us
#    Message - PWMCommand packet 0x07100AXX
#              OR
#              MultiCommand packet 0x07000AXX
#              (would require figuring out how many I need to send)
pwm_packet = can2pwm.PWMCommandPacket(pwm = 900)
pwm_msg = can2pwm.make_message(pwm_packet, 0xFF)
bus.send(pwm_msg)

# 2. Step over range: 900 - 1200us
# 60us steps should give 2mm
for step in range(900, 2100, 60):
    print(f"Stepping: {step}")
    pwm_packet = can2pwm.PWMCommandPacket(pwm = step)
    pwm_msg = can2pwm.make_message(pwm_packet, 0xFF)
    bus.send(pwm_msg)
    time.sleep(2)

# Shut down the notifier thread
# TODO RAII
notifier.stop()
csv_listener.stop()

# Shut down the bus
# TODO RAII
bus.shutdown()
