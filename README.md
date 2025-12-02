---
author: lbrinston
title: Readme
---

# Requirements

The intention of this project is to provide the groundwork to make
programmatic interactions with CANBus devices easy. The `python-can`
library already provides most of this.

1.  Message data encoding - from human readable variables to a bytearray
    (the format used by the `can.Message.data`) Ideally messages can be
    written something like
    `setNodeIDPacket(serialNumber = <serial number>, ...)` as oppose to
    having to hand craft bytes.
2.  Message decoding Some easy way to set up message decoding from
    bytearray to human readable values for use by Printers and Loggers
3.  CAN ID decoding Some easy way to map CAN IDs to more human readable
    names
4.  Configurable logging
    1.  User should be able to easily specify which messages get logged
    2.  User should be able to easily specify which fields of a message
        get logged
    3.  Logging configuration should be settable either directly in
        script or loaded from a config file
    4.  User should be able to easily specify a variety of different
        logging levels (ie. absolute log of all messages seen, pretty
        printing, filtered csv output)
    5.  User should be able to specify a logging format (csv, mf4, etc)
    6.  User should be able to provide a filename and path for the
        logging file
5.  Should make creation of CANBus filters easier than doing hex masking
    by hand
6.  Should be easily extendable to other CANbus devices

## Target Audience

The target audience for this library is engineers not programmers (at
least not python programmers). The end user is expected to be familiar
with CANbus but looking for a more script-able means of interacting with
CANbus devices (often lacking in manufacturer tooling).

To this end the interface for this library should not be <u>so
pythonic</u> that a C programmer could not understand what is going on.
However, where language features offer sufficient advantage their
workings should be documented for the benefit and edification of the end
user (see: [Python Primer](id:ed668e6a-3f44-435f-b86d-4465d4bc349b)
below).

# Code at Current Date

At current (\[2025-12-02 Tue\]) the code makes no attempt to abstract
over the CANbus message passing paradigm. Instead an ICD in the form of
python `dataclasses` is provided in `Currawong/can2pwm_icd.py`. These
`dataclasses` provide an easy way to de/encode the messages supported by
the Currawong can2pwm modules (no head math for decimal to hex
required), for example:

``` python
telem_packet = can2pwm.TelemetrySettingsPacket(period=100, silence=100, 
                                               packets=0, statusA=True, 
                                               statusB=True)
# Create a broadcast message - 0xFF
telem_message = can2pwm.make_message(telem_packet, 0xFF)
bus.send(telem_message)
```

The above snippet creates `TelemetrySettingsPacket` object which can
then be passed to the `can2pwm.make_message(packet, nodeID)` method
which returns a `can.Message`. Transmission of CAN messages is performed
in the typical procedural manner.

Receiving and processing of received messages is handled by a
`Notifier-Listener` scheme. This is a threading based approach provided
by the `python-can` library ([python-can: Notifier and
Listener](https://python-can.readthedocs.io/en/stable/notifier.html) ).
A Notifier thread dispatches messages to Listener threads which process
the messages. The `python-can` libraries provide a number of Notifiers
and Listeners however, they are all geared toward logging the CAN
message as is (no decoding).

The `can2pwm` namespace provides a `CSVListener` class that allows for
more granular control over logging via a logging configuration object
which looks like this:

``` python
log_config = {
    'PWMCommandPacket': can2pwm.PacketLogConfig(enabled=True, fields=['pwm']),
    'statusAPacket': can2pwm.PacketLogConfig(enabled=True, fields=['feedback', 'command']),
    'statusBPacket': can2pwm.PacketLogConfig(enabled=True, fields=['current', 'voltage'])
}
```

The logging config is a dictionary who's keys <u>must</u> match the
packet dataclass to be logged. It's values are `PacketLogConfig`
constructs that take an `enabled` boolean and `fields` list (here again,
the field names <u>must</u> match the fields of the Packet dataclass to
be logged). This allows the end user to specify which packets and which
fields from those packets to log.

`Note`: `fields=None` is interpreted as log all fields for that packet.
Omission of the packet entirely from the log configuration will silence
the packet.

# Testing

## Unit tests

This project to date does contain a small number of unit tests for the
Packet dataclasses (see `./tests/test_dataclasses.py`). In order to use
them:

1.  You must have set up the project virtual environment (venv)
2.  You must have installed `python-can` into the venv
3.  You must have installed `pytest` into the venv
4.  Run `pytest ./tests/test_dataclasses.py` from the project root

At current just trying to run:

1.  `./tests/test_dataclasses.py` will return a
    `ModuleNotFoundError: No Module named 'Currawong'`
2.  `python3 -m -tests/test_dataclasses.py` will return
    `Relative Module Names not Supported`

Both of these are due to the insane way Python's module import system
works.

# Design Methodology

The following relies on the `python-can` library (module?) to provide
the CANbus functionality while the manufacturer and device specific
details are implemented from scratch to provide a interface to the data
contained in the CAN messages.

## Classes & Inheritance - Manufacturer & Specific Devices

Currawong Engineering uses the Piccolo can format for their CANbus IDs
and many of their devices support the same set of CAN message (plus or
minus certain fields).

    # | 0x00    | 0x00         | 0x00        | 0x00           |
    # | GroupID | Message Type | Device Type | Device Address |
    # | 5 bits  | 8 bits       | 8 bits      | 8 bits         |

This means a class and inheritance based implementation provides an
intuitive level of organization.

Currawong \# Base class from with device specific classes inherit Servo
\# Device specific class CAN2PWM

The base class (currawong) provides class variables and methods that are
common to all Currawong devices. Device specific subclasses provide
class variables and methods specific to those devices.

## Dataclasses - CAN message ICD

Python's dataclasses provide functionality similar to structs in C. As
their name suggests they are specialized classes[^1]. Dataclasses look
just like regular python classes but with the == decorator applied (see:
[Decorators](id:7f487164-efda-46b5-9289-2836c70db85c) for a primer) and
type hints (see: [Type hints](id:30277157-1734-4cbd-94e8-e7df8af66492))
applied to it's class variables.

<div class="captioned-content">

<div class="caption">

An example dataclass with class variables for the CAN message fields,
shifts, and masks (the latter two upcased to evoke C style \#defines).
Two dataclass methods are provide to convert data two and from their
byte level representation.

</div>

``` python
from dataclass import dataclass
from typing import Optional

@dataclass
class ExampleCANMessage:
    # Message field variables
    example_field1: int
    example_field2: int

    # Message field manipulation variables
    FIELD_NAME_SHIFT = 24
    FIELD_NAME_MASK = 0xFF

    def to_bytes(self):
        # ...
    @classmethod    
    def from_bytes(cls, data):
        # ...
```

</div>

All CAN messages are provided in the `currawong_icd.py` file and
imported into the `currawong.py`. Messages that are common to all
Currawong devices are provide by instantiating at the `currawong` (base
class) level and device specific messages are provided by instantiation
in the device class.

# Questions

## Question How can the `python-can` Notifier-Listener structure be generalized to data processing (digital filters)?

## Question How can does Listener-Notifier compare to the CANBridge?

Notifiers work in a similar manner to the CANGatekeeper task of the
CANBridge. However, the CANbridge benefits from having hardware level
CAN filters (python-can support of filters is interface dependant) and a
filter match lookup table.

## Question How do I pipe data between sending and receiving threads? How would I create feedback loops?

## Question How could we measure performance?

## Question How much processing can we do in python before it becomes prohibitive?

# Python Primer - For the C programmer

## Decorators

<div class="BACKLINKS drawer">

\[2025-11-22 Sat 11:23\] \<- [Dataclasses - CAN message
ICD](id:8c44b2e4-cdc7-41c3-ab02-1861f3113e4d)

</div>

Decorators are a form metaprogramming that allow the extension of
already defined functions and methods. In essence they are a clever way
of implementing a wrapper around a function. In order to grasp them it
is important remember that function (and methods) are objects in Python.
This means that variables can hold functions and functions can be passed
as objects. So decorators themselves are functions that take another
function as an argument and provides an environemnt around the use of
that function to extend it.

A common (and intuitive) use case for decorators is to

## Type hints

<div class="BACKLINKS drawer">

\[2025-11-22 Sat 11:29\] \<- [Dataclasses - CAN message
ICD](id:8c44b2e4-cdc7-41c3-ab02-1861f3113e4d)

</div>

Python is a dynamically typed language and relies on duck typing[^2].
While this can be convent at times it can lead to ambiguity and mistakes
that are not discovered until runtime. To help with this Python provides
type hinting via the `typing` module. `Note` these are what they say on
the tin: <u>hints</u>. These are no enforced like in statically typed
languages such as C. Type hints are also picked up by IDEs and language
server protocols (LSPs) which means that it is possible to end up with
code that your IDE thinks is wrong but pyhon will runs (but it may not
behave as expected) or IDE completion refusing to show methods that you
know an object has (but your type hints would suggest otherwise).

Technically, python would have you be as generic as possible
(contravariant) when it comes to type hinting for <u>inputs</u> but as
specific as possible (covariant) for <u>outputs</u>.

<div class="captioned-content">

<div class="caption">

Example type hints.

</div>

``` python
import typing

# Types hints for variables:
# <var>: <type>
# Type hints for a function return:
# def <func_name>(args) -> <type>
def example_func(stuff: int) -> float:
    return stuff
```

</div>

## Types

### `byte` - immutable

### `bytearray` - mutable

# Dependencies

# Python-can

This project relies on the `python-can` library (module?) to provide the
CANbus functionality while the manufacturer and device specific details
are implemented from scratch to provide a interface to the data
contained in the CAN messages.

# Issues & Gotchas

## Currawong Serial Numbers

For some reason the serial number field in the `SetNodeID packet` (U32)
and `SerialNumber packet` (U24) are different. I have no idea how big
Currawong serial numbers are actually supposed to be.

[^1]: Of course if you peak under the hook in C++ you will discovered
    that classes are in fact equivalent to specialized structs.

[^2]: If it walks like a duck and talks like a duck it's probably an
    integer.
