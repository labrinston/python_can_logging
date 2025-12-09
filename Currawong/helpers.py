#!/usr/bin/env python3

# --- Bit Helpers --- #
def get_bit(field: int, bit_position: int) -> int:
    """Gets the value of a single bit at a given position."""
    return (field >> bit_position) & 0x1


def set_bit(field: int, bit_position: int) -> int:
    """Sets a specific bit in a field to 1."""
    mask = 1 << bit_position
    return (field & ~mask) | mask


def clear_bit(field: int, bit_position: int) -> int:
    """Clears a specific bit in a field to 0."""
    mask = ~(1 << bit_position)
    return field & mask


def get_bits(field: int, mask: int, shift: int) -> int:
    """Gets the value of a range of bits using a mask and shift."""
    return (field & mask) >> shift


def set_bits(field: int, value: int, mask: int, shift: int) -> int:
    """Sets a range of bits in a field to a given value."""
    return (field & ~mask) | ((value << shift) & mask)
