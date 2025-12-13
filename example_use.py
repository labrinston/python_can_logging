#!/usr/bin/env python3

import time
import can
import logging
from Currawong.can2pwm_icd import can2pwm
from cli import commissioning_cli as cli

# ---- Handle Command-line Arguments ---- #

parser = cli.parse_cli()
args = parser.parse_args()

# ---- Configure Stdout Logging ---- #

logging.basicConfig(
    # Set based on cli args
    level=args.loglevel.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        # logging.FilerHandler('can2pwm.log'),
        logging.StreamHandler()
    ],
)
logger = logging.getLogger(__name__)

# ---- Bus Setup ---- #
# Linux
with can.Bus(channel="can0", interface="socketcan", receive_own_messages=True) as bus:

    # Windows
    # with can.Bus(channel="can0", interface="socketcan", receive_own_messages=True) as bus:

    # ---- Find Currawong Devices ---- #
    dev_tuple = can2pwm.discover_devices(bus)
    logger.info("Devices: %s", dev_tuple)
    if dev_tuple:
        print(f"Found: {dev_tuple}")
    else:
        response = input("No devices found on bus. Proceed?")
        if response.lower() != "y":
            exit(0)

    # ---- (Optional) Set NodeIDs ---- #

    if args.dev_ids:
        logger.info("Setting %s as new device IDs", args.dev_ids)
        print(f"Setting Device IDs: {args.dev_ids}")

        for (serial_num, curr_id), new_id in zip(dev_tuple, args.dev_ids):
            # for serial_num, curr_id in dev_tuple:
            #     for new_id in args.dev_ids:
            logger.info("Mapping - Serial No. %s to Device ID %s", serial_num, new_id)
            packet = can2pwm.setNodeIDPacket(serial_num, new_id)
            print(f"Packet: {packet}")
            message = can2pwm.make_message(packet, curr_id)
            print(f"setNodeID: {message}")
            bus.send(message)
    else:
        print("Skipping -- Set Device IDs (No IDs passed via --dev_ids).")
    # ---- Enable Telemetry ---- #

    # Enable statusA and statusB
    telem_packet = can2pwm.TelemetrySettingsPacket(
        period=100, silence=100, packets=0, statusA=True, statusB=True
    )
    # Create a broadcast message - 0xFF
    telem_message = can2pwm.make_message(telem_packet, 0xFF)
    logger.info("Sending: %s", telem_message)
    bus.send(telem_message)

    # Configure Analog feedback mode
    config_packet = can2pwm.configPacket(
        enabled=True,
        channel=0,
        reserved=0,
        timeout=0,
        timeoutAction=0,
        feedbackAction=4,  # 4 = Analog feedback
        commandEmulation=0,
    )
    config_message = can2pwm.make_message(config_packet, 0xFF)
    bus.send(config_message)
    logger.info("Sending: %s", config_message)

    # ---- Listener Setup ---- #

    # Create logging config (Note: this only applies to the can2pwm CSVListener)
    log_config = {
        "PWMCommandPacket": can2pwm.PacketLogConfig(enabled=True, fields=["pwm"]),
        "statusAPacket": can2pwm.PacketLogConfig(
            enabled=True,
            fields=[
                "feedbackMode",
                "validFeedback",
                "reserved",
                "feedback",
                "command",
                "pwm",
            ],
        ),
        "statusBPacket": can2pwm.PacketLogConfig(
            enabled=True, fields=["current", "voltage"]
        ),
    }

    # Request listeners from the can2pwm module
    print_listener = can2pwm.PrintListener()
    csv_listener = can2pwm.CSVListener(
        log_dir=args.log_dir, log_name=args.file_name, log_config=log_config
    )

    # Provide the csv_listener to the notifier
    # Reception and logging of CAN messages will be handled by a separate thread
    notifier = can.Notifier(bus, [csv_listener])

    # ---- Transmission ---- #

    time.sleep(2)

    # 1. Issue full retraction - 900us
    #    Message - PWMCommand packet 0x07100AXX
    #              OR
    #              MultiCommand packet 0x07000AXX
    #              (would require figuring out how many I need to send)
    pwm_packet = can2pwm.PWMCommandPacket(pwm=900)
    pwm_msg = can2pwm.make_message(pwm_packet, 0xFF)
    bus.send(pwm_msg)

    # 2. Step over range: 900 - 2100us (should be full range)
    # 60us steps should give 2mm
    STEP = 60
    START = 900
    STOP = (
        2100 + STEP
    )  # full range, NOTE: range() is exclusive of stop - hence the extra 60
    # STOP = 1200 + STEP  # shorter range for testing
    logger.info("Stepping from: %s to %s in steps of %s", START, STOP, STEP)
    for step in range(START, STOP, STEP):
        logger.info("Stepping: %s", step)
        pwm_packet = can2pwm.PWMCommandPacket(pwm=step)
        pwm_msg = can2pwm.make_message(pwm_packet, 0xFF)
        bus.send(pwm_msg)
        time.sleep(2)

    # 3. Sweep over full - no steps
    # 3.1 Retract
    pwm_packet = can2pwm.PWMCommandPacket(pwm=900)
    pwm_msg = can2pwm.make_message(pwm_packet, 0xFF)
    bus.send(pwm_msg)

    # Wait? Don't currently have way to receive feedback via the main thread
    time.sleep(5)

    # 3.2 Extend
    pwm_packet = can2pwm.PWMCommandPacket(pwm=2100)
    pwm_msg = can2pwm.make_message(pwm_packet, 0xFF)
    bus.send(pwm_msg)

    # Wait? Don't currently have way to receive feedback via the main thread
    time.sleep(5)

    # 3.2 Retract
    pwm_packet = can2pwm.PWMCommandPacket(pwm=900)
    pwm_msg = can2pwm.make_message(pwm_packet, 0xFF)
    bus.send(pwm_msg)

    # Fin

    # Shut down the notifier thread
    # Will the bus context manager handle these?
    # TODO RAII
    notifier.stop()
    csv_listener.stop()
