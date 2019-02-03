#===========================================================================
#
# Insteon on/off device utilities.
#
#===========================================================================
import enum


#===========================================================================
class Mode(enum.Enum):
    """TODO: doc"""
    NORMAL = "normal"
    FAST = "fast"
    INSTANT = "instant"
    MANUAL = "manual"

    def __str__(self):
        return self.value

    @staticmethod
    def is_valid(cmd):
        """TODO: doc"""
        return cmd in _cmdMap

    @staticmethod
    def encode(is_on, mode):
        """TODO: doc"""
        assert isinstance(mode, Mode)
        if is_on:
            return _onCode[mode]
        else:
            return _offCode[mode]

    @staticmethod
    def decode(cmd):
        """TODO: doc"""
        result = _cmdMap.get(cmd, None)
        if result is None:
            raise Exception("Invalid switch command %s.  Expected one of: %s"
                            % (cmd, str(_cmdMap.keys())))
        return result


#===========================================================================
# Map command code to [is_on, Mode]
_cmdMap = {0x11 : [True, Mode.NORMAL],
           0x12 : [True, Mode.FAST],
           0x21 : [True, Mode.INSTANT],
           0x23 : [True, Mode.MANUAL],
           0x13 : [False, Mode.NORMAL],
           0x14 : [False, Mode.FAST],
           # Per Insteon dev guide, there is no instant off.
           0x22 : [True, Mode.MANUAL]}

# Map enum mode to command code for on and off.
_onCode = {v[1] : k for k, v in _cmdMap.items() if v[0] is True}
_offCode = {v[1] : k for k, v in _cmdMap.items() if v[0] is False}

# Instant off is the same as instant on, just with the level set to 0x00.
_offCode[Mode.INSTANT] = _onCode[Mode.INSTANT]
