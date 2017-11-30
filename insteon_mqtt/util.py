#===========================================================================
#
# Misc utilities
#
#===========================================================================
import binascii
import io
import logging


def to_hex(data, num=None, space=' '):
    """Convert a byte array to a string of hex.

    Args:
       data:   (bytes) Bytes array to output.
       num:    (int) Number of bytes to output or None for all.
       space:  (str) String to space out the byte outputs.

    Returns:
       (str) Returns a string of the printed bytes.
    """
    if num:
        data = data[:num]

    hex_str = binascii.hexlify(data).decode()

    o = io.StringIO()
    for i in range(0, len(hex_str), 2):
        if i:
            o.write(space)
        o.write(hex_str[i])
        o.write(hex_str[i + 1])

    return o.getvalue()

#===========================================================================

# TODO: doc this stuff
UI = 21
logging.addLevelName(UI, "UI")

class Logger(logging.getLoggerClass()):
    def ui(self, msg, *args, **kwargs):
        if self.isEnabledFor(UI):
            self._log(UI, msg, args, **kwargs)

def get_logger(name):
    return Logger(name)

#===========================================================================
