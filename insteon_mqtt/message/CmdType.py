#===========================================================================
#
# Insteon Command Types
#
#===========================================================================
# flake8: noqa

__doc__ = """Insteon Command Types

These are used in InpStandard, InpExtended, OutStandard, and OutExtended.
Most of the are unique, but a few commands numbers do have multiple meanings.
Because of this, do not rely on the conversion of a value to a name to be
a one to one relationship, you may end up with a different name that you
expect, so maybe don't use in logging.  However, becuase of enums, logical
comarisions will still work correctly.

There are likely additional commands that are not in this list.
"""

import enum

class CmdType(enum.IntEnum):
    ASSIGN_TO_GROUP = 0x01
    DELETE_FROM_GROUP = 0x02
    LINK_CLEANUP_REPORT = 0x06
    LINKING_MODE = 0x09
    UNLINKING_MODE = 0x0A
    GET_ENGINE_VERSION = 0x0D
    PING = 0x0F
    ID_REQUEST = 0x10
    ON = 0x11
    ON_FAST = 0x12
    OFF = 0x13
    OFF_FAST = 0x14
    BRIGHT = 0x15
    DIM = 0x16
    START_MANUAL_CHANGE = 0x17
    STOP_MANUAL_CHANGE = 0x18
    STATUS_REQUEST = 0x19
    GET_OPERATING_FLAGS = 0x1f
    SET_OPERATING_FLAGS = 0x20
    ON_INSTANT = 0x21
    OFF_MANUAL = 0x22
    ON_MANUAL = 0x23
    DO_READ_EE = 0x24
    REMOTE_SET_BUTTON_TAP = 0x25
    SET_LED_STATUS = 0x27
    SPRINKLER_STATUS = 0x27
    SET_ADDRESS_MSB = 0x28
    POKE = 0x29
    POKE_EXTENDED = 0x2a
    PEEK = 0x2b
    PEEK_INTERNAL = 0x2c
    POKE_INTERNAL = 0x2d
    EXTENDED_SET_GET = 0x2e
    READ_WRITE_ALDB = 0x2f
    SPRINKLER_VALVE_ON = 0x40
    SPRINKLER_VALVE_OFF = 0x41
    SPRINKLER_PROGRAM_ON = 0x42
    SPRINKLER_PROGRAM_OFF = 0x43
    SPRINKLER_CONTROL = 0x44
    SPRINKLER_TIMERS_REQUEST = 0x45
    OUTPUT_RELAY_ON = 0x45
    OUTPUT_RELAY_OFF = 0x46
    WRITE_OUTPUT_PORT = 0x48
    READ_INPUT_PORT = 0x49
    GET_SENSORS_VALUE = 0x4A
    EZIO_CONTROL = 0x4F
    THERMOSTAT_TEMP_UP = 0x68
    THERMOSTAT_TEMP_DOWN = 0x69
    THERMOSTAT_GET_ZONE_INFO = 0x6a
    THERMOSTAT_CONTROL = 0x6b
    THERMOSTAT_SETPOINT_COOL = 0x6c
    THERMOSTAT_SETPOINT_HEAT = 0x6d
    IMETER_RESET = 0x80
    IMETER_QUERY = 0x82
