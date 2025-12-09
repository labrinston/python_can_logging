#!/usr/bin/env python3

import csv
import logging
from datetime import datetime
from can import Listener, Message
import dataclasses
import os
import time
from .packets import PacketLogConfig


from .enums import deviceType

logger = logging.getLogger(__name__)

class CSVListener(Listener):
        """
        Custom CSV listener that allows packet level logging configuration.
        Can specify:
        - What packets to log
        - What fields in those packets to log
        - Log file name
        """

        # Use init to inject additional objects
        def __init__(self, log_dir, log_name, log_config=None):
            """

            args:
                - log_dir: Path to a dir for logging.
                - log_name: Base name for the CSV log.
                - log_config: A dict of a PacketLogConfig objects.
                -
            """
            # self.message_registry = message_registry
            self.log_dir = log_dir
            self.log_name = log_name
            self.csv_files = {}

            # Create the csv file
            date_slug = "_" + time.strftime("%Y-%m-%d %H:%M:%S")
            file_path = log_dir + "/" + log_name + date_slug
            logger.info("Creating: %s", file_path)
            if os.path.exists(file_path):
                response = input(f"File {file_path} exists. Overwrite?")
                if response.lower() == "y":
                    os.makedirs(log_dir, exist_ok=True)
                    self.log_path = file_path
                    self.csv_file = open(f"{file_path}.csv", "w", newline="")
                else:
                    response = input(f"New name?")
                    file_path = file_path + response + date_slug
                    print(f"Writing to: {file_path}.")
                    self.csv_file = open(f"{file_path}.csv", "w", newline="")
            else:
                self.csv_file = open(f"{file_path}.csv", "w", newline="")
                logger.info("Creating: %s", file_path)

            # Create the csv writer
            logger.info("Creating CSV writer...")
            self.csv_writer = csv.writer(self.csv_file)

            # Add optional flexibility here
            # Dict -> Dataclass conversion?

            # If no config was passed, use the default
            if log_config is None:
                logger.info("No CSVLog config specified. Applying defaults.")
                self.log_config = {
                    "statusAPacket": PacketLogConfig(
                        enabled=True, fields=["feedback", "command"]
                    ),
                    "statusBPacket": PacketLogConfig(
                        enabled=True, fields=["current", "voltage"]
                    ),
                }
            else:
                # Otherwise
                self.log_config = {
                    # Handle:
                    # 1. Plain Dicts - via dict comprehension to unpack (**) into a dataclass
                    # 2, Dict of datclasses - use as is and log into self
                    name: (
                        PacketLogConfig(**cfg) if isinstance(cfg, dict) else cfg
                    )
                    for name, cfg in log_config.items()
                }
            logger.info("Configuring CSVLogging with:\n%s", self.log_config)

            # Write headers
            header_row = self._setup_table()
            logger.debug("Writing: %s", header_row)
            self.csv_writer.writerow(header_row)

        def _setup_table(self):
            """Creates csv header and calculates csv leaders and trailers for each packet that is configured to
            be logged."""

            # This should probably just be a class variable
            message_registry_by_name = {
                cls.__name__: cls for cls in message_registry.values()
            }
            default_headers = [
                "timestamp",
                "CAN ID",
                "device ID",
            ]  # Must be prepended _after_ header setup

            # Dynamic Header Setup
            #  0 1 2 3 4 5  Index
            # |P|P|X|X|N|N|
            #  1 2 3 4 5 6  Length
            #      ^ ^-- end
            #      |---- beg(in)
            #
            # where.
            # P,X,N - some set of specified fields
            #
            # leader - # of empty cells to be prepended to a field
            # = beg
            # trailer - # of empty cells to be appended to a field
            # = len(table) - beg
            headers = []
            beg = 0
            end = 0
            for packet_name, config in self.log_config.items():

                if not config.enabled:
                    continue

                PacketClass = message_registry_by_name.get(packet_name)
                logger.debug(f"Setting up: {PacketClass}")
                if not PacketClass:
                    continue

                # Get fields config
                fields = config.fields
                logger.debug(f"Fields: {fields}")

                # Concatenate headers
                headers += PacketClass.csv_header(fields)

                # Store position information in config
                config._csv_beg = beg
                config._csv_end = len(headers)
                beg = config._csv_end  # next
                # print(
                #     f"beg: {beg} | csv_beg: {config._csv_beg} | csv_end: {config._csv_end}"
                # )
                # print(f"Config: {packet_name} with {config}")

            table_len = len(headers)
            # print(f"Table length: {table_len}")

            # Loop again and set csv_leader/csv_trailer
            for packet_name, config in self.log_config.items():
                config._csv_leader = (config._csv_beg) * [""]
                config._csv_trailer = (table_len - config._csv_end) * [""]

            # print("At END of _setup_table:")
            # for name, cfg in self.log_config.items():
            # print(f"  {name}: type={type(cfg)}")

            # Attach default headers:
            headers = default_headers + headers

            return headers

        def on_message_received(self, msg):

            # Parse the CAN ID
            device_type = (msg.arbitration_id >> 8) & 0xFF
            device_addr = msg.arbitration_id & 0xFF
            msg_type = (msg.arbitration_id >> 16) & 0xFF

            # Check if the message is from a can2pwm device
            device_type = (msg.arbitration_id >> 8) & 0xFF
            if device_type != deviceType.CAN2PWM.value:
                return

            # Check that we have a data class to decode the data
            PacketClass = message_registry.get(msg_type)
            if not PacketClass:
                logger.info("Unknown message type: %s", hex(msg_type))
                return

            # Decode the data
            packet = PacketClass.from_can_bytes(msg.data)
            packet_name = PacketClass.__name__
            config = self.log_config.get(packet_name, {})
            logger.debug("Decoded packet:\n%s", packet)

            # if not config.get('enabled', True):
            # if self.config or not self.config.enabled:
            #     return

            fields_to_log = config.fields

            csv_data = packet.to_csv(fields_to_log)
            defaults = (
                [datetime.fromtimestamp(msg.timestamp)]
                + [f"{msg.arbitration_id:X}"]
                + [f"{(msg.arbitration_id & 0xFF):X}"]
            )
            csv_str = defaults + config._csv_leader + csv_data + config._csv_trailer

            # Write to file here
            self.csv_writer.writerow(csv_str)
            self.csv_file.flush()

        def __call__(self, msg: Message) -> None:
            self.on_message_received(msg)

        def stop(self):
            # Do clean up here
            self.csv_file.close()

        def on_error(self, exc: Exception) -> None:
            raise NotImplementedError()