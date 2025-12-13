#!/usr/bin/env python3

import csv
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from can import Listener, Message
import dataclasses
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

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
    mask = 1 << bit_position
    return (field & ~mask) | mask


def clear_bit(field: int, bit_position: int) -> int:
    """Set specific bits in a field to a value."""
    mask = 0 << bit_postion
    return field & (0 << bit_position)


def get_bits(field: int, mask: int, shift: int) -> int:
    return (field & mask) >> shift


def set_bits(field: int, value: int, mask: int, shift: int) -> int:
    """Set specific bits in a field to a value."""
    return (field & ~mask) | ((value << shift) & mask)


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


class can2pwm:

    DEVICE_TYPE = 0x0A

    # ---- Python-CAN Listener ---- #
    #
    class PrintListener(Listener):
        def on_message_received(self, msg: Message) -> None:
            """Simple example of a print listener."""
            print(f"Rx: {msg}")

        def __call__(self, msg: Message) -> None:
            self.on_message_received(msg)

        def on_error(self, exc: Exception) -> None:
            raise NotImplementedError()

    @dataclass
    class PacketLogConfig:
        # fmt: off
        enabled: bool = True
        fields: list = None
        _csv_beg: int = 0
        _csv_end: int = 0
        _csv_leader: str = ""
        _csv_trailer: str = ""
        # fmt: on

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
            date_slug = "_" + time.strftime("%Y-%m-%d_%H-%M-%S")
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
                    "statusAPacket": can2pwm.PacketLogConfig(
                        enabled=True, fields=["feedback", "command"]
                    ),
                    "statusBPacket": can2pwm.PacketLogConfig(
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
                        can2pwm.PacketLogConfig(**cfg) if isinstance(cfg, dict) else cfg
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
                cls.__name__: cls for cls in can2pwm.message_registry.values()
            }
            default_headers = [
                "Timestamp",
                "CAN ID",
                "Packet Name",
                "Device ID",
                "Payload (Raw)",
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
            if device_type != can2pwm.DEVICE_TYPE:
                return

            # Check that we have a data class to decode the data
            PacketClass = can2pwm.message_registry.get(msg_type)
            if not PacketClass:
                logger.info("Unknown message type: %s", hex(msg_type))
                return

            # Decode the data
            packet = PacketClass.from_can_bytes(msg.data)
            packet_name = PacketClass.__name__
            packet_name_clean = packet_name.strip("{}'")
            config = self.log_config.get(packet_name, {})
            raw_data = "".join(f"{byte:02X}" for byte in msg.data)
            # logger.info("Decoded packet:\n%s", packet)

            # if not config.get('enabled', True):
            # if self.config or not self.config.enabled:
            #     return

            fields_to_log = config.fields

            csv_data = packet.to_csv(fields_to_log)
            # logger.info("CSV data: %s", csv_data)
            defaults = (
                [datetime.fromtimestamp(msg.timestamp)]
                + [f"{msg.arbitration_id:X}"]
                + [f"{packet_name_clean}"]
                + [f"{(msg.arbitration_id & 0xFF):X}"]
                + [f"{raw_data}"]
            )
            csv_str = defaults + config._csv_leader + csv_data + config._csv_trailer
            # logger.info("CSV row: %s", csv_str)

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

    @dataclass
    class PacketBase:
        """Base class for Currawong CANbus data packets"""

        message_type = None

        def to_bytes(self) -> bytearray:
            """Converts to wire format from dataclass fields."""

        @classmethod
        def from_bytes(cls, data: bytes):
            """Converts to dataclass fields from wire format."""

        # Does it make sense to do this here?
        @classmethod
        def csv_header(cls, fields=None):
            # print(f"Creating csv headers for: {fields}")
            if fields is None:
                return [f.name for f in dataclasses.fields(cls)]
            else:
                # Should probably validate the fields so we can fail at header construction instead of on data retrival
                # logger.info("Fields to log: %s", fields)
                return fields

        def to_csv(self, fields=None):
            if fields is None:
                # This should convert things to a string
                # for f in dataclasses.fields(self):
                return [f"{getattr(self, f.name)}" for f in dataclasses.fields(self)]
            else:
                return [f"{getattr(self, field)}" for field in fields]

    @dataclass
    class MultiCommandPacket:
        """"""

        # fmt: off
        commandA : int  # 0..1 I16
        commandB : int  # 2..3 I16
        commandC : int  # 3..4 I16
        commandD : int  # 4..5 I16

        message_type  = 0x00
        INPUT_LIM_POS = 20000
        INPUT_LIM_NEG = -20000
        # fmt: on

        def __init__(self, offset, commandA, commandB, commandC, commandD):

            if not self.INPUT_LIM_NEG > commandA > self.INPUT_LIM_POS:
                raise ValueError(
                    f"commandA out of range: {commandA}. Min: {self.INPUT_LIM_NEG} Max: {self.INPUT_LIM_POS}"
                )
            if not self.INPUT_LIM_NEG > commandB > self.INPUT_LIM_POS:
                raise ValueError(
                    f"commandB out of range: {commandB}. Min: {self.INPUT_LIM_NEG} Max: {self.INPUT_LIM_POS}"
                )
            if not self.INPUT_LIM_NEG > commandC > self.INPUT_LIM_POS:
                raise ValueError(
                    f"commandC out of range: {commandC}. Min: {self.INPUT_LIM_NEG} Max: {self.INPUT_LIM_POS}"
                )
            if not self.INPUT_LIM_NEG > commandD > self.INPUT_LIM_POS:
                raise ValueError(
                    f"commandD out of range: {commandD}. Min: {self.INPUT_LIM_NEG} Max: {self.INPUT_LIM_POS}"
                )

            self.commandA = commandA
            self.commandB = commandB
            self.commandC = commandC
            self.commandD = commandD

        def to_can_bytes(self):
            return bytearray(
                [
                    *self.commandA.to_bytes(1, "big", signed=True),
                    *self.commandB.to_bytes(1, "big", signed=True),
                    *self.commandC.to_bytes(1, "big", signed=True),
                    *self.commandD.to_bytes(1, "big", signed=True),
                ]
            )

    @dataclass
    class PWMCommandPacket(PacketBase):
        """"""

        pwm: int  # 0..1 I16 [us]
        message_type = 0x10

        def to_can_bytes(self):
            return bytearray([*self.pwm.to_bytes(2, "big", signed=True)])

        @classmethod
        def from_can_bytes(cls, data):
            """"""
            if data is None:
                return cls(None)

            pwm = int.from_bytes(data[0:3], "big", signed=True)

            return cls(pwm=pwm)

    # ----- Eng Commands Packets        ----- #

    # ----- Begin Status Packets      ----- #

    # Message Type - 0x60
    @dataclass
    class statusAPacket(PacketBase):
        """Base structure of the statusA Telemetry Packet"""

        # Message fields (Instance variables)
        # fmt: off
        # Byte 0
        status        : int                     # 0..1     U16
        inputMode     : "can2pwm.inputModes"    # 0:7..0:5 B3
        feedbackMode  : "can2pwm.feedbackModes" # 0:4..0:2 B3
        validInput    : bool                    # 0:1      B1
        validFeedback : bool                    # 0:0      B0
        # Byte 1
        enabled       : bool                    # 1:7      B1
        reserved      : int                     # 1:6..1:2 B5
        mapEnabled    : bool                    # 1:1      B1
        mapInvalid    : bool                    # 1:0      B1
        # Bytes 2-7
        command       : int                     # 2..3     I16
        feedback      : int                     # 4..5     U16 Actual PWM value
        pwm           : int                     # 6..7     U16 [us]

        # Class Variable
        message_type         = 0x60
        # Masks & shifts
        # Status 0..1
        # Byte 0
        _input_mode_mask      = 0xC0   # 0:7..0:5
        _input_mode_shift     = 5
        _feedback_mode_mask   = 0x1C   # 0:4..0:2
        _feedback_mode_shift  = 2
        _valid_input_bit      = 1      # 0:1
        _valid_feedback_bit   = 0      # 0:0
        # Byte 1
        _enabled_bit          = 15     # 1:7
        _reserved_mask        = 0x7C00 # 1:6..1:2
        _reserved_shift       = 10
        _map_enabled_bit      = 9      # 1:1
        _map_invalid_bit      = 8      # 1:0
        # fmt: on

        # Telemetry is only received therefore no to_bytes method is needed
        # EXCEPT - if you're polling, in which case data = []
        # def to_can_bytes(self):
        #     # status_value = (*self.status.to_bytes(2, "big"))
        #     return bytearray(
        #         [
        #             # 0..1
        #             *self.status.to_bytes(2, "big"),
        #             # 2..3
        #             *self.command.to_bytes(2, "big", signed=True),
        #             # 4..5
        #             *self.feedback.to_bytes(2, "big"),
        #             # 6..7
        #             *self.pwm.to_bytes(2, "big"),
        #         ]
        #     )

        @classmethod
        def from_can_bytes(cls, data):

            # fmt: off
            status_value   = int.from_bytes(data[0:2], "big")
            command_value  = int.from_bytes(data[2:4], "big", signed=True)
            feedback_value = int.from_bytes(data[4:6], "big")
            # logger.info("Feedback: %s", feedback_value)
            pwm_value      = int.from_bytes(data[6:8], "big")
            return cls(
                status        = status_value,
                inputMode     = get_bits(
                    status_value, cls._input_mode_mask, cls._input_mode_shift
                ),
                feedbackMode  = get_bits(
                    status_value, cls._feedback_mode_mask, cls._feedback_mode_shift
                ),
                validInput    = bool(get_bit(status_value, cls._valid_input_bit)),
                validFeedback = bool(get_bit(status_value, cls._valid_feedback_bit)),
                # Byte 1
                enabled       = bool(get_bit(status_value, cls._enabled_bit)),
                reserved      = get_bits(status_value, cls._reserved_mask, cls._reserved_shift),
                mapEnabled    = bool(get_bit(status_value, cls._map_enabled_bit)),
                mapInvalid    = bool(get_bit(status_value, cls._map_invalid_bit)),
                command       = command_value,
                feedback      = feedback_value,
                pwm           = pwm_value,
                # fmt: on
            )

    # Message Type - 0x61
    @dataclass
    class statusBPacket(PacketBase):
        """statusA Telemetry Packet

        0..1 Current I16 10mA per bit
        2..3 Voltage U16 10mV per bit
        """

        # fmt: off
        # Message data (instance variables)
        current: int  # 0..1 I16 [mA]
        voltage: int  # 2..3 U16 [mV]

        # Masks & shifts (class variables)
        message_type = 0x61
        PACKET_LEN = 4
        # fmt: on

        def to_can_bytes(self):

            # 1. Scale to 10mA/mV per bit
            # // floor divide
            current_scaled = self.current // 10
            voltage_scaled = self.voltage // 10

            # 2. Handle current sign - bitwise & will treat negatives appropriately
            current_bytes = current_scaled & 0xFFFF

            data = bytearray(
                [
                    *current_scaled.to_bytes(2, "big", signed=True),
                    *voltage_scaled.to_bytes(2, "big", signed=False),
                ]
            )
            return data

        @classmethod
        def from_can_bytes(cls, data):
            current_scaled = int.from_bytes(data[0:2], "big", signed=True) * 10
            voltage_scaled = int.from_bytes(data[2:4], "big", signed=False) * 10

            return cls(current=current_scaled, voltage=voltage_scaled)

    # ----- Eng Status Packets        ----- #

    # ----- Begin Configuration Packets ----- #

    # serialNumberPacket
    # Message Type - 0x70
    @dataclass
    class serialNumberPacket:
        """Base structure of Telemetry Message"""

        # fmt: off
        hwRev        : int = None  # 0    U8
        serialNumber : int = None  # 1..3 U24
        userIDA      : int = None  # 4..5 U16
        userIDB      : int = None  # 6..7 U16
        message_type       = 0x70
        # fmt: on

        def to_can_bytes(self):
            """Converts from internal dataclass values to big endian bytearray."""
            return bytearray(
                [
                    # 0
                    *(self.hwRev).to_bytes(1, "big"),
                    # 1..3
                    *(self.serialNumber).to_bytes(3, "big"),
                    # 4..5
                    *(self.userIDA).to_bytes(2, "big"),
                    *(self.userIDB).to_bytes(2, "big"),
                ]
            )

        @classmethod
        def from_can_bytes(cls, data):
            """Converts from bytearray to dataclass internal varialbes."""

            # This is needed to catch broadcast packets
            # Otherwise we'll run aground on an IndexError
            if len(data) == 0:
                return cls(None)
            else:
                hw = data[0]
                serial = int.from_bytes(data[1:4], "big")
                IDA = int.from_bytes(data[4:6], "big")
                IDB = int.from_bytes(data[6:8], "big")
            return cls(hwRev=hw, serialNumber=serial, userIDA=IDA, userIDB=IDB)

    # Message Type - 0x74
    @dataclass
    class TelemetrySettingsPacket:
        """Base structure of Telemetry Message"""

        # fmt: off
        period    : int               # 0        U8 [ms] 0-10s
        silence   : int               # 1        U8 [ms] 0-10s
        packets   : int               # 2        U8
        statusA   : bool              # 2:7      B1
        statusB   : bool              # 2:6      B1
        _reserved : int = 0           # 2:5..2:0 B6

        STATUS_A_BIT    = 7
        STATUS_B_BIT    = 6
        MASK_RESERVED   = 0x1F
        message_type    = 0x74
        # statusC: Optional[int] = None # reference
        # fmt: on

        def __init__(self, period, silence, statusA, statusB, _reserved=0, packets=0):
            # Validate user input
            if period < 50 and period > 0 or period > 10000:
                raise ValueError(
                    "Period is set in increments of 50ms. Minimum: 50ms | Maximum: 10,000ms"
                )
            if silence < 50 and silence > 0 or silence > 10000:
                raise ValueError(
                    "Silence is set in increments of 50ms. Minimum: 50ms | Maximum: 10,000ms"
                )
            if not isinstance(statusA, bool):
                raise ValueError("statusA may only be set via bool.")
            if not isinstance(statusB, bool):
                raise ValueError("statusB may only be set via bool.")

            self.period = period
            self.silence = silence
            self.statusA = statusA
            self.statusB = statusB
            self.packets = packets
            self._reserved = _reserved
            if self.statusA is True:
                self.packets = set_bit(self.packets, self.STATUS_A_BIT)
            if self.statusB is True:
                self.packets = set_bit(self.packets, self.STATUS_B_BIT)

        def to_can_bytes(self):
            period_scaled = self.period // 50
            silence_scaled = self.silence // 50
            print(f"Period: {period_scaled} | Silence: {silence_scaled}")
            if self.statusA is True:
                self.packets = set_bit(self.packets, self.STATUS_A_BIT)
            else:
                self.packets = clear_bit(self.packets, self.STATUS_A_BIT)
            if self.statusB is True:
                self.packets = set_bit(self.packets, self.STATUS_B_BIT)
            else:
                self.packets = clear_bit(self.packets, self.STATUS_B_BIT)
            print(f"Packets: {self.packets:04X}")
            data = bytearray([period_scaled, silence_scaled, self.packets])
            return data

        @classmethod
        def from_can_bytes(cls, data):
            scaled_period = data[0] * 50
            scaled_silence = data[1] * 50
            packets_byte = data[2]
            return cls(
                period=scaled_period,
                silence=scaled_silence,
                packets=packets_byte,
                statusA=bool(get_bit(packets_byte, cls.STATUS_A_BIT)),
                statusB=bool(get_bit(packets_byte, 6)),
                _reserved=packets_byte & cls.MASK_RESERVED,
            )

    @dataclass
    class configPacket:
        """Base structure of Config Packet"""

        # TODO: Decide how to handle the "piccolo" field:
        # - should it be exposed at all?
        # - if it is exposed - setting piccolo, [enabled, channel, reserved] should be mutually exclusive
        # fmt: off
        enabled          : bool       # 0:7      B1 
        channel          : int        # 0:6..0:2 B5
        reserved         : int        # 0:1..0:0 B2
        timeout          : int        # 1        U8 100ms per bit
        timeoutAction    : int        # 2:7..2:5 B3
        feedbackAction   : int        # 2:4..2:2 B3
        commandEmulation : int        # 2:1..2:0 B2
        home             : int = None # 3..4     U16 (Optional) [us]
        _piccolo         : int = 0    # 0        U8
         
        message_type             = 0x80
        min_bytes                = 3
        max_bytes                = 5
        # Byte 0
        _enabled_shift           = 7
        _enabled_mask            = 0x80
        _channel_shift           = 2
        _channel_mask            = 0x7C
        _reserved_shift          = 0
        _reserved_mask           = 0x03
        # Byte 2
        _timeoutAction_shift     = 5
        _timeoutAction_mask      = 0xE0
        _feedbackAction_shift    = 2
        _feedbackAction_mask     = 0x1A
        _commandEmulation_shift  = 0
        _commandEmulation_mask   = 0x03
        # fmt: on

        def __post_init__(self):
            # Build the piccolo field from enabled, channel, reserved
            self._piccolo = (
                (int(self.enabled) << self._enabled_shift)
                | (self.channel << self._channel_shift)
                | (self.reserved << self._reserved_shift)
            )
            if self.timeout % 100:
                raise ValueError(
                    f"Timeout must be a min. and divisible by 100ms (0 = no timeout). Got: {self.timeout}"
                )

        def to_can_bytes(self):
            byte2_value = (
                (self.timeoutAction << self._timeoutAction_shift)
                | (self.feedbackAction << self._feedbackAction_shift)
                | (self.commandEmulation << self._commandEmulation_shift)
            )
            timeout_val = self.timeout // 100
            # Home is optional - check if it was supplied
            if self.home is not None:
                data = bytearray(
                    [
                        # Byte 0
                        *(self._piccolo).to_bytes(1, "big"),
                        # Byte 1
                        *(timeout_val).to_bytes(1, "big"),
                        # Byte 2
                        *(byte2_value).to_bytes(1, "big"),
                        # Bytes 3..4
                        *(self.home).to_bytes(2, "big"),
                    ]
                )
            else:
                data = bytearray(
                    [
                        # Byte 0
                        *(self._piccolo).to_bytes(1, "big"),
                        # Byte 1
                        *(self.timeout).to_bytes(1, "big"),
                        # Byte 2
                        *byte2_value.to_bytes(1, "big"),
                    ]
                )

            print(f"Encode data bytes: {data.hex()}")
            return data

        @classmethod
        def from_can_bytes(cls, data):

            piccolo_byte = data[0]
            # timeoutAction_val = get_bits(
            #     data[2], cls._timeoutAction_mask, cls._timeoutAction_shift
            # )
            if len(data) == cls.min_bytes:
                home_val = None
            elif len(data) == cls.max_bytes:
                home_val = int.from_bytes(data[3:5], "big")
            else:
                raise ValueError(
                    f"Data length error! Expected {cls.min_bytes}-{cls.max_bytes}bytes data. Got {len(data)}"
                )
            return cls(
                # Byte 0
                _piccolo=piccolo_byte,
                enabled=bool(get_bit(piccolo_byte, cls._enabled_shift)),
                channel=get_bits(piccolo_byte, cls._channel_mask, cls._channel_shift),
                reserved=get_bits(
                    piccolo_byte, cls._reserved_mask, cls._reserved_shift
                ),
                # Byte 1
                timeout=data[1] * 100,
                # Byte 2
                timeoutAction=get_bits(
                    data[2], cls._timeoutAction_mask, cls._timeoutAction_shift
                ),
                feedbackAction=get_bits(
                    data[2], cls._feedbackAction_mask, cls._feedbackAction_shift
                ),
                commandEmulation=get_bits(
                    data[2], cls._commandEmulation_mask, cls._commandEmulation_shift
                ),
                # Bytes 3..4
                home=home_val,
            )

    # ----- End Configuration Packets   ----- #
    # ----- System Command Packets      ----- #
    @dataclass
    class setNodeIDPacket:
        """Base structure of Set Node ID Packet"""

        # fmt: off
        command      : int  # 0    U8
        serialNumber : int  # 1..4 U32 <-- wtf SerialNumber packet is U24??
        nodeID       : int  # 5    U8

        message_type  = 0x50
        COMMAND       = 0x50
        PACKET_LENGTH = 5  # bytes
        # fmt: on

        def __init__(self, serialNumber, nodeID, command=0x50):
            self.command = command
            self.serialNumber = serialNumber
            self.nodeID = nodeID

        def to_can_bytes(self):
            data = bytearray(
                [
                    self.command,
                    *self.serialNumber.to_bytes(4, "big"),
                    *self.nodeID.to_bytes(1, "big"),
                ]
            )
            return data

        @classmethod
        def from_can_bytes(cls, data):
            serial = int.from_bytes(data[1:5], "big")
            return cls(command=data[0], serialNumber=serial, nodeID=data[5])

    # ----- End System Command Packets  ----- #

    # can2pwm message registry
    # TODO there has got to be a less manual way of doing this
    message_registry = {
        0x10: PWMCommandPacket,
        0x50: setNodeIDPacket,
        0x60: statusAPacket,
        0x61: statusBPacket,
        0x80: configPacket,
    }

    # ---- Helper Methods --------- #

    def make_message(packet, nodeID):
        can_id = (0x07 << 24) | (packet.message_type << 16) | (0x0A << 8) | nodeID
        message = Message(arbitration_id=can_id, data=packet.to_can_bytes())
        return message

    def discover_devices(bus):
        """Discovers devices of DEVICE_TYPE connected to BUS by broadcast of a request for serial number.
        args:
             - device_type: The Currawong device ID field to broadcast too
        returns:
             - Device tuple in the form : [(serial_number, device_address)]
        """

        # ?Setup filter for serialNumber packets?

        # Setup broadcast of SerialNumber packet
        broadcast_id = 0xFF
        device_type = 0x0A << 8  # TODO replace with enum
        can_id_base = 0x07700000 | device_type
        can_id = can_id_base | broadcast_id
        msg = Message(arbitration_id=can_id, data=[])

        # Broadcast the message
        bus.send(msg)

        # Listen for responses for 2 seconds
        seen_serials = set()
        devices_tuple = []
        start = time.time()
        while time.time() - start < 2:
            try:
                rx_msg = bus.recv(timeout=0.1)  # 100ms timeout
            except can.CanOperationError as e:
                print(f"Error sending: {e}")

            if rx_msg is None:
                # print(f"No devices responded too: {can_id}")
                continue

            # Need to validate that the packet we're checking is a serialNumberPacket
            addr = rx_msg.arbitration_id & 0xFFFFFF00
            deviceID = rx_msg.arbitration_id & 0xFF

            # We only want SerialNumberPackets from devices (_not_ the broadcast address 0xFF)
            if addr == can_id_base and deviceID != 0xFF:
                packet = can2pwm.serialNumberPacket.from_can_bytes(rx_msg.data)
                if packet.serialNumber not in seen_serials:

                    seen_serials.add(packet.serialNumber)

                    # Only add to our device list if it's a new serial number
                    deviceID = rx_msg.arbitration_id & 0xFF

                    devices_tuple.append((packet.serialNumber, deviceID))

        # Notify user if we didn't find any devices
        if devices_tuple is None:
            print(f"No devices responded to: {can_id:X}")

        # ?Clear filters?
        # bus.set_filters(filters = None)

        return devices_tuple


# ------------------------------ #
