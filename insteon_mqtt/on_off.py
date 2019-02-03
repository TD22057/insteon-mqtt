#===========================================================================
#
# Insteon on/off device utilities.
#
#===========================================================================
import enum


#===========================================================================
class Type(enum.Enum):
    NORMAL = "normal"
    FAST = "fast"
    INSTANT = "instant"
    MANUAL = "manual"

    def __str__(self):
        return self.value

    @staticmethod
    def is_valid(cmd):
        return cmd in _cmdMap

    @staticmethod
    def encode(is_on, type):
        assert isinstance(type, Type)
        if is_on:
            return _onCode[type]
        else:
            return _offCode[type]

    @staticmethod
    def decode(cmd):
        result = _cmdMap.get(cmd, None)
        if result is None:
            raise Exception("Invalid switch command %s.  Expected one of: %s"
                            % (cmd, str(_cmdMap.keys())))
        return result


#===========================================================================
# Map command code to [is_on, Type]
_cmdMap = {0x11 : [True, Type.NORMAL],
           0x12 : [True, Type.FAST],
           0x21 : [True, Type.INSTANT],
           0x23 : [True, Type.MANUAL],
           0x13 : [False, Type.NORMAL],
           0x14 : [False, Type.FAST],
           # Per Insteon dev guide, there is no instant off.
           0x22 : [True, Type.MANUAL]}

# Map enum type to code for on and off.
_onCode = {v[1] : k for k, v in _cmdMap.items() if v[0] is True}
_offCode = {v[1] : k for k, v in _cmdMap.items() if v[0] is False}
# Instant off is the same as instant on, just with the level set to 0x00.
_offCode[Type.INSTANT] = _onCode[Type.INSTANT]
