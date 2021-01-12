#===========================================================================
#
# Insteon on/off command utilities and constants.
#
#===========================================================================
import enum

# Constants used for the built in reasons.

# Device button being pressed or initiating the change.
REASON_DEVICE = "device"
# Device responding to a scene command.
REASON_SCENE = "scene"
# Device responding to a direct command.
REASON_COMMAND = "command"
# Device state from a refresh command.
REASON_REFRESH = "refresh"


#===========================================================================
class Mode(enum.Enum):
    """On/Off command mode enumeration.

    There are various flavors of on/off commands to most Insteon devices.
    This enum captures those flavors and handles converting between the enum
    and the Insteon command codes for them.
    """
    NORMAL = "normal"
    FAST = "fast"
    INSTANT = "instant"
    # this is manual load status change, not holding down a button
    MANUAL = "manual"
    RAMP = "ramp"

    def __str__(self):
        return str(self.value)

    @staticmethod
    def is_valid(cmd):
        """See if a command code is a valid on/off code.
        Args:
          cmd (int):   The Insteon command code
        Returns:
          bool: Returns True if the input is a valid on/off code
        """
        return cmd in _cmdMap

    @staticmethod
    def encode(is_on, mode):
        """Convert on/off and a mode enumeration to a command code.

        Args:
          is_on (bool):  True for on, False for off.
          mode (Mode):   The mode enumeration to use.
        Returns:
          int: Returns the Insteon command code for the input.
        """
        assert isinstance(mode, Mode)
        if is_on:
            return _onCode[mode]
        else:
            return _offCode[mode]

    @staticmethod
    def decode(cmd):
        """Convert a command code to on/off and a mode enumeration.

        If the input isn't a valid command code, an Exception is thrown.

        Args:
          cmd (int):  The Insteon on/off command code.

        Returns:
          (bool, Mode):  Returns a tuple of an on/off boolean and the mode
          enum.
        """
        result = _cmdMap.get(cmd, None)
        if result is None:
            raise Exception("Invalid switch command %s.  Expected one of: %s"
                            % (cmd, str(_cmdMap.keys())))
        return result

    @staticmethod
    def encode_cmd2(is_on, mode, level, transition):
        """Convert on/off, mode, level, and transition to a cmd2 value.

        Args:
          is_on (bool):        True for on, False for off.
          mode (Mode):         The mode enumeration to use.
          level (int):         Brighness value in range 0 to 255.
          transition (float):  Ramp time in seconds.
        Returns:
          int: Returns the Insteon cmd2 value for the input.
        """
        # Mapping of half-ramp rates to human readable values
        half_ramp_pretty = {0x00: 480, 0x01: 360, 0x02: 270, 0x03: 210,
                            0x04: 150, 0x05: 90, 0x06: 47, 0x07: 38.5,
                            0x08: 32, 0x09: 28, 0x0a: 23.5, 0x0b: 19,
                            0x0c: 6.5, 0x0d: 2, 0x0e: .3, 0x0f: .1}
        assert isinstance(mode, Mode)
        if not is_on:
            level = 0
        if mode == Mode.RAMP:
            if transition is None:
                transition = 2
            half_ramp = 0x0f
            for ramp_key, ramp_value in half_ramp_pretty.items():
                if transition >= ramp_value:
                    half_ramp = ramp_key
                    break
            level = level & 0xf0
            return level | half_ramp
        else:
            return level

    @staticmethod
    def decode_level(cmd1, cmd2):
        is_on, mode = Mode.decode(cmd1)
        if not is_on:
            return 0x00
        elif mode == Mode.RAMP:
            # Special case - lower 4 bits are treated as 0xf by device
            return cmd2 | 0x0f
        else:
            return cmd2

#===========================================================================
# It would be better if these were part of Mode - but python < 3.7 doesn't
# support adding attributes to an enum that are enumeration values.


# Map command code to [is_on, Mode enum]
_cmdMap = {0x11 : [True, Mode.NORMAL],
           0x12 : [True, Mode.FAST],
           0x21 : [True, Mode.INSTANT],
           0x23 : [True, Mode.MANUAL],
           0x2e : [True, Mode.RAMP],
           0x13 : [False, Mode.NORMAL],
           0x14 : [False, Mode.FAST],
           # Per Insteon dev guide, there is no instant off - it's instant on
           # with level set to 0.
           0x22 : [False, Mode.MANUAL],
           0x2f : [False, Mode.RAMP]}

# Map enum mode to command code for on and off.
_onCode = {v[1] : k for k, v in _cmdMap.items() if v[0] is True}
_offCode = {v[1] : k for k, v in _cmdMap.items() if v[0] is False}

# Instant off is the same as instant on, just with the level set to 0x00.
_offCode[Mode.INSTANT] = _onCode[Mode.INSTANT]


#===========================================================================
class Manual(enum.Enum):
    """On/Off manual mode enumeration.

    There are the various manual mode commands that Insteon devices send when
    a button is held down.  UP or DOWN is sent when pressed, OFF is sent when
    the button is released.
    """
    UP = "up"
    DOWN = "down"
    STOP = "stop"

    def __str__(self):
        return str(self.value)

    @staticmethod
    def is_valid(cmd):
        """See if a command code is a valid on/off code.
        Args:
          cmd (int):  The Insteon command code
        Returns:
          bool: Returns True if the input is a valid on/off code
        """
        return cmd in (0x17, 0x18)

    @staticmethod
    def encode(manual):
        """Convert manual  enumeration to a pair of command codes.

        Args:
          manual (Mode):  The mode enumeration to use.
        Returns:
          (int, int): Returns the Insteon code 1 and code 2 for the input.
        """
        assert isinstance(manual, Manual)
        if manual is Manual.STOP:
            return 0x18, 0x00
        elif manual is Manual.UP:
            return 0x17, 0x01
        else:
            return 0x17, 0x00

    @staticmethod
    def decode(cmd1, cmd2):
        """Convert a pair of command codes to manual enumeration.

        If the input isn't a valid command code, an Exception is thrown.

        Args:
          cmd1 (int):   The Insteon command code 1.  0x17=start, 0x18=stop
          cmd2 (int):   The Insteon command code 2.  Ignored for stop.
                        For start, 0x01=up, 0x00=down.

        Returns:
          Manual: Returns the manual enum.
        """
        if cmd1 == 0x18:
            return Manual.STOP
        elif cmd1 == 0x17:
            if cmd2 == 0x01:
                return Manual.UP
            elif cmd2 == 0x00:
                return Manual.DOWN

        raise Exception("Invalid manual command %s, %s." % (cmd1, cmd2))

    def int_value(self):
        """Return an integer value of the command code.

        Returns:
          int: UP = +1, STOP = 0, DOWN = -1
        """
        if self is Manual.UP:
            return +1
        elif self is Manual.DOWN:
            return -1
        else:
            return 0

    def openhab_value(self):
        """Return an integer value of the command code for OpenHab.

        Returns:
          int: OpenHab uses UP = 2, STOP = 1, DOWN = 0.
        """
        if self is Manual.UP:
            return 2
        elif self is Manual.DOWN:
            return 0
        else:
            return 1
