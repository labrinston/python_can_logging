#!/usr/bin/env python3
import argparse

# This file provides a _basic_ command-line interface for the example_use.py file at
# the root of this project


def valid_device_id(value):
    """
    Validates that the passed value is within the 0x00-0xFE
    """
    try:
        ivalue = int(value, 0)  # Automatically detects base (e.g., hex)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid device ID: {value}")

    # Check the range and exclusion
    if 0 <= ivalue <= 0xFE:
        return ivalue
    elif ivalue == 0xFF:
        raise argparse.ArgumentTypeError(
            f"Got: {value}, this is the broadcast address and may not be used as a device ID."
        )
    else:
        raise argparse.ArgumentTypeError(
            f"Device  must be between 0 and 0xFE (inclusive), but got: {value}"
        )


def parse_cli():
    """Parses commandline args (using argparse) for the Currawong CAN2PWM commissioning script."""

    parser = argparse.ArgumentParser(
        description="Currawong CAN2PWM-MightyZap commissioning script\n"
    )

    # File path to write logs too
    parser.add_argument(
        "-ld",
        "--log_dir",
        type=str,
        default="./",  # TODO change to ./logs and add logic to check for/create dir
        help="Path at which to create log files.",
    )

    # File name for logs
    parser.add_argument(
        "-f",
        "--file_name",
        type=str,
        default="mightyzap_comm",
        help="Base name for log files.",
    )

    # (Optional) List of device IDs to set
    parser.add_argument(
        "-i",
        "--dev_ids",
        # nargs
        # '+' == 1 or more
        # '*' == 0 or more
        # '?' == 0 or 1
        nargs="*",
        action="append",
        type=valid_device_id,
        # choices=list(range(0x00, 0xFF, 0x01)),
        help="List of device IDs to set.",
    )

    parser.add_argument(
        "-log",
        "--loglevel",
        default="info",
        choices=["noset", "debug", "info", "warning", "error", "critical"],
        help="Provide logging level. Example --loglevel debug, default=info",
    )
    return parser


# This allows the cli to be called independently for testing purposes.
if __name__ == "__main__":
    parser = parse_cli()
    args = parser.parse_args()
    print(f"{args}")
