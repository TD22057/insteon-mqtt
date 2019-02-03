#===========================================================================
#
# Insteon on/off command utilities.
#
#===========================================================================
import enum


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
    MANUAL = "manual"

    def __str__(self):
        return self.value

    @staticmethod
    def is_valid(cmd):
        """See if a command code is a valid on/off code.
        Args:
          cmd:  (int) The Insteon command code
        Returns:
          Returns True if the input is a valid on/off code
        """
        return cmd in _cmdMap

    @staticmethod
    def encode(is_on, mode):
        """Convert on/off and a mode enumeration to a command code.

        Args:
          is_on:  (bool) True for on, False for off.
          mode:   (Mode) The mode enumeration to use.
        Returns:
          (int) Returns the Insteon command code for the input.
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
          cmd:    (int) The Insteon on/off command code.

        Returns:
          (bool, Mode) Returns a tuple of an on/off boolean and the mode enum.
        """
        result = _cmdMap.get(cmd, None)
        if result is None:
            raise Exception("Invalid switch command %s.  Expected one of: %s"
                            % (cmd, str(_cmdMap.keys())))
        return result


#===========================================================================

# Map command code to [is_on, Mode enum]
_cmdMap = {0x11 : [True, Mode.NORMAL],
           0x12 : [True, Mode.FAST],
           0x21 : [True, Mode.INSTANT],
           0x23 : [True, Mode.MANUAL],
           0x13 : [False, Mode.NORMAL],
           0x14 : [False, Mode.FAST],
           # Per Insteon dev guide, there is no instant off.
           0x22 : [False, Mode.MANUAL]}

# Map enum mode to command code for on and off.
_onCode = {v[1] : k for k, v in _cmdMap.items() if v[0] is True}
_offCode = {v[1] : k for k, v in _cmdMap.items() if v[0] is False}

# Instant off is the same as instant on, just with the level set to 0x00.
_offCode[Mode.INSTANT] = _onCode[Mode.INSTANT]
