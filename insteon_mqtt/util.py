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
    """Convert a controller boolean flag to a string description.
    """
    if is_controller:
        return "CTRL"
    else:
        return "RESP"


#===========================================================================
def bit_get(value, bit):
    """Get a bit from an integer.

    Args:
      value:  (int) The value to get the bit from.
      bit:    (int) The bit (0..n) to return.

    Returns:
      Returns the value (0 or 1) of the requested bit.
    """
    return (value >> bit) & 1


#===========================================================================
def bit_set(value, bit, is_one):
    """Set a bit in an integer.

    Args:
      value:  (int) The value to set the bit into.
      bit:    (int) The bit (0..n) to return.
      is_one: (bool) True to set the bit to 1, False to set it to 0.

    Returns:
      Returns the new value with the bit set to the input.
    """
    if is_one:
        return value | (1 << bit)
    else:
        return value & ~(1 << bit)


#===========================================================================
def resolve_data3(defaults, inputs):
    """TODO: doc
    """
    values = []

    for i in range(3):
        if inputs is None or inputs[i] == -1:
            values.append(defaults[i])
        else:
            values.append(inputs[i])

    return bytes(values)


#===========================================================================
def input_choice(inputs, field, choices):
    """TODO: doc
    """
    value = inputs.pop(field, None)
    if value is None:
        return None

    if isinstance(value, str):
        value = value.lower()

    if value not in choices:
        msg = "Invalid %s input.  Valid inputs are on of %s" % \
              (value, str(choices))
        raise ValueError(msg)

    return value


#===========================================================================
def input_bool(inputs, field):
    """TODO: doc
    """
    value = inputs.pop(field, None)
    if value is None:
        return None

    lv = value.lower()
    if lv == "true":
        value = True
    elif lv == "false":
        value = False

    try:
        # Use int() because bool("asdf") also returns true.  This insures
        # only true/false or 1/0 is allowed.
        return bool(int(value))
    except ValueError:
        msg = "Invalid %s input.  Valid inputs are 1/0 or True/False" % input
        raise ValueError(msg)


#===========================================================================
def input_byte(inputs, field):
    """TODO: doc
    """
    value = inputs.pop(field, None)
    if value is None:
        return None

    try:
        if '0x' in value:
            v = int(value, 16)
        else:
            v = int(value)

        if v < 0 or v > 255:
            raise ValueError("Value out of range")

        return v
    except ValueError:
        msg = "Invalid %s input.  Valid inputs are 0-255" % input
        raise ValueError(msg)
