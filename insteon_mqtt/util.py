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
    """Merge default 3 byte list with an input list.

    Creates a byte array of length 3.  If the inputs list element i is not
    -1, it's used.  Otherwise defaults[i] is used.

    Inputs:
      defaults:   (list) List of 3 byte values to use for the defaults.
      inputs:     (list) List of 3 byte values of inputs.  Use -1
                  at an element to use the default.  Enter None to use all
                  defaults.

    Returns:
      (bytes) Returns a 3 byte array.
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
    """User input enum utility.

    Extracts inputs[field] and compares it against the valid list of choices.
    Throws a ValueError if the input is not in choices.  Strings are
    converted to lower case before matching.

    Inputs:
      inputs:   (dict) Dict of input keyword arguments.  The input field is
                removed from this dict.
      field:    (str) The field to get from inputs.
      choices:  [] The valid list of values for field.  For strings, should
                be all lower case.

    Returns:
      Returns the selected input value.  If field doesn't exist in inputs,
      None is returned.  String values are converted to lower case.
    """
    # Extract the field and convert to lower case.
    value = inputs.pop(field, None)
    if value is None:
        return None

    if isinstance(value, str):
        value = value.lower()

    # Check the value against the valid options for the field.
    if value not in choices:
        msg = "Invalid %s input.  Valid inputs are on of %s" % \
              (value, str(choices))
        raise ValueError(msg)

    return value


#===========================================================================
def input_bool(inputs, field):
    """User input bool utility.

    Extracts inputs[field] and compares it against the valid inputs for a
    boolean: 0, 1, "true", or "false".  Throws a ValueError if the input is
    not a valid boolean

    Inputs:
      inputs:   (dict) Dict of input keyword arguments.  The input field is
                removed from this dict.
      field:    (str) The field to get from inputs.

    Returns:
      Returns the field boolean value.  If field doesn't exist in inputs,
      None is returned.
    """
    value = inputs.pop(field, None)
    if value is None:
        return None

    if isinstance(value, str):
        lv = value.lower()
        if lv == "true":
            value = True
        elif lv == "false":
            value = False

    try:
        # Use int() because bool("asdf") also returns true.  This ensures
        # only true/false or 1/0 is allowed.
        return bool(int(value))
    except ValueError:
        msg = "Invalid %s input.  Valid inputs are 1/0 or True/False" % input
        raise ValueError(msg)


#===========================================================================
def input_byte(inputs, field):
    """User input byte utility.

    Extracts inputs[field] and compares it against the valid inputs for a
    byte: integer of string containing 0xXX.  Throws a ValueError if the
    input is not an integer or in the range [0, 255].

    Inputs:
      inputs:   (dict) Dict of input keyword arguments.  The input field is
                removed from this dict.
      field:    (str) The field to get from inputs.

    Returns:
      Returns the field integer value.  If field doesn't exist in inputs,
      None is returned.
    """
    value = inputs.pop(field, None)
    if value is None:
        return None

    try:
        if isinstance(value, str) and '0x' in value:
            v = int(value, 16)
        else:
            v = int(value)

        if v < 0 or v > 255:
            raise ValueError("Value out of range")

        return v
    except ValueError:
        msg = "Invalid %s input.  Valid inputs are 0-255" % input
        raise ValueError(msg)
