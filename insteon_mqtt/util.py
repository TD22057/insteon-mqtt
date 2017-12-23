#===========================================================================
#
# Misc utilities
#
#===========================================================================
import binascii
import io


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
def make_callback(callback):
    """Insure that callback is a valid function.

    This is used when callbacks are optional.  It makes it so the
    class can store the callback even if one wasn't entered so that it
    can just be used.  If the input is None, then a dummy callback
    that does nothing is returned.
    """
    if not callback:
        return lambda *x: None
    else:
        return callback


#===========================================================================
def ctrl_str(is_controller):
    """ TODO: doc
    """
    if is_controller:
        return "CTRL"
    else:
        return "RESP"


#===========================================================================
