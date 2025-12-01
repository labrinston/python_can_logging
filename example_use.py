#!/usr/bin/env python3

import can
import time
from Currawong.can2pwm_icd import can2pwm

# Setup the bus
# Linux
bus = can.Bus(channel = 'can0', interface='socketcan')
# Windows
# bus = can.Bus(channel = '?', interface='pcan') # TODO channel param for windows

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

# TODO Example transmission code

time.sleep(10)

# Shut down the notifier thread
# TODO RAII
notifier.stop()

# Shut down the bus
# TODO RAII
bus.shutdown()
