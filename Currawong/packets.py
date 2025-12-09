#!/usr/bin/env python3

import dataclasses
from dataclasses import dataclass

from .enums import feedbackModes, inputModes
from .helpers import get_bit, set_bit, clear_bit, get_bits, set_bits





# --- Packet Base Class --- #
@dataclass
class PacketBase:
    """Base class for Currawong CANbus data packets"""

    message_type = None

    def to_bytes(self) -> bytearray:
        """Converts to wire format from dataclass fields."""
        raise NotImplementedError

    @classmethod
    def from_bytes(cls, data: bytes):
        """Converts to dataclass fields from wire format."""
        raise NotImplementedError

    @classmethod
    def csv_header(cls, fields=None):
        if fields is None:
            return [f.name for f in dataclasses.fields(cls)]
        else:
            return fields

    def to_csv(self, fields=None):
        if fields is None:
            return [f"{getattr(self, f.name)}" for f in dataclasses.fields(self)]
        else:
            return [f"{getattr(self, field)}" for field in fields]


# --- Command Packets --- #
@dataclass
class MultiCommandPacket(PacketBase):
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

        if not self.INPUT_LIM_NEG < commandA < self.INPUT_LIM_POS:
            raise ValueError(
                f"commandA out of range: {commandA}. Min: {self.INPUT_LIM_NEG} Max: {self.INPUT_LIM_POS}"
            )
        if not self.INPUT_LIM_NEG < commandB < self.INPUT_LIM_POS:
            raise ValueError(
                f"commandB out of range: {commandB}. Min: {self.INPUT_LIM_NEG} Max: {self.INPUT_LIM_POS}"
            )
        if not self.INPUT_LIM_NEG < commandC < self.INPUT_LIM_POS:
            raise ValueError(
                f"commandC out of range: {commandC}. Min: {self.INPUT_LIM_NEG} Max: {self.INPUT_LIM_POS}"
            )
        if not self.INPUT_LIM_NEG < commandD < self.INPUT_LIM_POS:
            raise ValueError(
                f"commandD out of range: {commandD}. Min: {self.INPUT_LIM_NEG} Max: {self.INPUT_LIM_POS}"
            )

        self.commandA = commandA
        self.commandB = commandB
        self.commandC = commandC
        self.commandD = commandD

    def to_bytes(self):
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

    def to_bytes(self):
        return bytearray([*self.pwm.to_bytes(2, "big", signed=True)])

    @classmethod
    def from_bytes(cls, data):
        """"""
        if data is None:
            return cls(None)

        pwm = int.from_bytes(data[0:2], "big", signed=True)

        return cls(pwm=pwm)


# --- Status Packets --- #

# Message Type - 0x60
@dataclass
class statusAPacket(PacketBase):
    """Base structure of the statusA Telemetry Packet"""

    # Message fields (Instance variables)
    # fmt: off
    status        : int
    inputMode     : inputModes
    feedbackMode  : feedbackModes
    validInput    : bool
    validFeedback : bool
    enabled       : bool
    reserved      : int
    mapEnabled    : bool
    mapInvalid    : bool
    command       : int
    feedback      : int
    pwm           : int

    # Class Variable
    message_type         = 0x60
    # Masks & shifts
    INPUT_MODE_MASK      = 0xC0
    INPUT_MODE_SHIFT     = 5
    FEEDBACK_MODE_MASK   = 0x1B
    FEEDBACK_MODE_SHIFT  = 2
    ENABLED_MASK         = 0x8000
    ENABLED_SHIFT        = 15
    RESERVED_MASK        = 0x7C00
    RESEREVED_SHIFT      = 10
    MAP_ENABLED_MASK     = 0x200
    MAP_ENABLED_SHIFT    = 9
    MAP_INVALID_MASK     = 0x100
    MAP_INVALID_SHIFT    = 8
    # fmt: on

    @classmethod
    def from_bytes(cls, data):
        status_value = int.from_bytes(data[0:2], "big")
        command_value = int.from_bytes(data[2:4], "big", signed=True)
        feedback_value = int.from_bytes(data[4:6], "big")
        pwm_value = int.from_bytes(data[6:8], "big")
        return cls(
            status=status_value,
            inputMode=inputModes(get_bits(
                status_value, cls.INPUT_MODE_MASK, cls.INPUT_MODE_SHIFT
            )),
            feedbackMode=feedbackModes(get_bits(
                status_value, cls.FEEDBACK_MODE_MASK, cls.FEEDBACK_MODE_SHIFT
            )),
            validInput=bool(get_bit(status_value, 1)),
            validFeedback=bool(get_bit(status_value, 0)),
            enabled=bool(get_bit(status_value, 15)),
            reserved=get_bits(status_value, cls.RESERVED_MASK, 2),
            mapEnabled=bool(get_bit(status_value, 9)),
            mapInvalid=bool(get_bit(status_value, 8)),
            command=command_value,
            feedback=feedback_value,
            pwm=pwm_value,
        )

# Message Type - 0x61
@dataclass
class statusBPacket(PacketBase):
    """statusB Telemetry Packet"""
    # fmt: off
    current: int  # 0..1 I16 [mA]
    voltage: int  # 2..3 U16 [mV]

    message_type = 0x61
    # fmt: on

    def to_bytes(self):
        current_scaled = self.current // 10
        voltage_scaled = self.voltage // 10

        data = bytearray(
            [
                *current_scaled.to_bytes(2, "big", signed=True),
                *voltage_scaled.to_bytes(2, "big", signed=False),
            ]
        )
        return data

    @classmethod
    def from_bytes(cls, data):
        current_scaled = int.from_bytes(data[0:2], "big", signed=True) * 10
        voltage_scaled = int.from_bytes(data[2:4], "big", signed=False) * 10

        return cls(current=current_scaled, voltage=voltage_scaled)


# --- Configuration Packets --- #

# Message Type - 0x70
@dataclass
class serialNumberPacket(PacketBase):
    """serialNumberPacket Telemetry Packet"""

    # fmt: off
    hwRev        : int = None
    serialNumber : int = None
    userIDA      : int = None
    userIDB      : int = None
    message_type       = 0x70
    # fmt: on

    def to_bytes(self):
        return bytearray(
            [
                *(self.hwRev).to_bytes(1, "big"),
                *(self.serialNumber).to_bytes(3, "big"),
                *(self.userIDA).to_bytes(2, "big"),
                *(self.userIDB).to_bytes(2, "big"),
            ]
        )

    @classmethod
    def from_bytes(cls, data):
        if len(data) == 0:
            return cls(None)
        else:
            hw = data[0]
            serial = int.from_bytes(data[1:4], "big")
            IDA = int.from_bytes(data[4:6], "big")
            IDB = int.from_bytes(data[6:8], "big")
        return cls(hwRev=hw, serialNumber=serial, userIDA=IDA, userIDB=IDB)

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
# Message Type - 0x74
@dataclass
class TelemetrySettingsPacket(PacketBase):
    """TelemetrySettingsPacket Configuration Packet"""

    # fmt: off
    period    : int
    silence   : int
    packets   : int
    statusA   : bool
    statusB   : bool
    _reserved : int = 0

    STATUS_A_BIT    = 7
    STATUS_B_BIT    = 6
    MASK_RESERVED   = 0x1F
    message_type    = 0x74
    # fmt: on

    def __init__(self, period, silence, statusA, statusB, _reserved=0, packets=0):
        if period % 50 != 0 and period > 0 or period > 10000:
            raise ValueError(
                "Period is set in increments of 50ms. Minimum: 50ms | Maximum: 10,000ms"
            )
        if silence % 50 != 0 and silence > 0 or silence > 10000:
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
        if self.statusA:
            self.packets = set_bit(self.packets, self.STATUS_A_BIT)
        if self.statusB:
            self.packets = set_bit(self.packets, self.STATUS_B_BIT)

    def to_bytes(self):
        period_scaled = self.period // 50
        silence_scaled = self.silence // 50
        if self.statusA:
            self.packets = set_bit(self.packets, self.STATUS_A_BIT)
        else:
            self.packets = clear_bit(self.packets, self.STATUS_A_BIT)
        if self.statusB:
            self.packets = set_bit(self.packets, self.STATUS_B_BIT)
        else:
            self.packets = clear_bit(self.packets, self.STATUS_B_BIT)
        data = bytearray([period_scaled, silence_scaled, self.packets])
        return data

    @classmethod
    def from_bytes(cls, data):
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


# --- System Command Packets --- #
@dataclass
class setNodeIDPacket(PacketBase):
    """setNodeIDPacket System Command Packet"""

    # fmt: off
    command      : int
    serialNumber : int
    nodeID       : int

    message_type  = 0x50
    COMMAND       = 0x50
    # fmt: on

    def __init__(self, serialNumber, nodeID, command=0x50):
        self.command = command
        self.serialNumber = serialNumber
        self.nodeID = nodeID

    def to_bytes(self):
        data = bytearray(
            [
                self.command,
                *self.serialNumber.to_bytes(4, "big"),
                *self.nodeID.to_bytes(1, "big"),
            ]
        )
        return data

    @classmethod
    def from_bytes(cls, data):
        serial = int.from_bytes(data[1:5], "big")
        return cls(command=data[0], serialNumber=serial, nodeID=data[5])

# --- Message Registry --- #
message_registry = {
    0x00: MultiCommandPacket,
    0x10: PWMCommandPacket,
    0x50: setNodeIDPacket,
    0x60: statusAPacket,
    0x61: statusBPacket,
    0x70: serialNumberPacket,
    0x74: TelemetrySettingsPacket,
}
