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
      data (bytes): Bytes array to output.
      num (int):  Number of bytes to output or None for all.
      space (str):  String to space out the byte outputs.

    Returns:
      str: Returns a string of the printed bytes.
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

    This is used when callbacks are optional.  It makes it so the class can
    store the callback even if one wasn't entered so that it can just be
    used.  If the input is None, then a dummy callback that does nothing is
    returned.

    Args:
      callback:  Input callback function or None.

    Returns:
      Returns the input callback or a dummy lambda function if the input is
      None.
    """
    if not callback:
        return lambda *x: None
    else:
        return callback


#===========================================================================
def ctrl_str(is_controller):
    """Convert a controller boolean flag to a string description.

    Args:
      is_controller (bool):  Controller/responder flag.

    Returns:
      str: "CTRL" or "RESP"
    """
    if is_controller:
        return "CTRL"
    else:
        return "RESP"


#===========================================================================
def bit_get(value, bit):
    """Get a bit from an integer.

    Args:
      value (int):  The value to get the bit from.
      bit (int):  The bit (0..n) to return.

    Returns:
      int: Returns the value (0 or 1) of the requested bit.
    """
    return (value >> bit) & 1


#===========================================================================
def bit_set(value, bit, is_one):
    """Set a bit in an integer.

    Args:
      value (int): The value to set the bit into.
      bit (int):  The bit (0..n) to return.
      is_one (bool): True to set the bit to 1, False to set it to 0.

    Returns:
      int: Returns the new value with the bit set to the input.
    """
    if is_one:
        return value | (1 << bit)
    else:
        return value & ~(1 << bit)


#===========================================================================
def resolve_data3(defaults, inputs):
    """Turn a user input into a list of 3 bytes for link data.

    The user input can be None (use defaults).  Or a list of 3 values.  If a
    value is -1, then the default for that value is used.

    Args:
      defaults (bytes[3]):  Default values to use.
      inputs:  User input.

    Returns:
      bytes[3]: Returns a 3 byte list to use as the insteon link data.
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
    """Check a user input against a list of valid choices.

    Raises:
      If inputs[field] is not in the choices list, an exception is thrown.

    Args:
      inputs (dict):  Key/value pairs of user input fields.
      field (str):  The field to check.
      choices (list): Valid choices for the field.

    Returns:
      Returns the field from the input dict.  For strings, the valiue is
      always converted to lower case.  If the field doesn't exist in inputs,
      None is returned.
    """
    # Extract the field and convert to lower case.
    value = inputs.pop(field, None)
    if value is None:
        return None

    if isinstance(value, str):
        value = value.lower()

    # Check the value against the valid options for the field.
    if value not in choices:
        msg = ("Invalid %s input.  Valid inputs are on of %s" %
               (value, str(choices)))
        raise ValueError(msg)

    return value


#===========================================================================
def input_bool(inputs, field):
    """Convert an input field to a boolean.

    Valid boolean inputs are 'true', 'false', 'on', 'off', 1, 0, True,
    or False.

    Raises:
      If the input is not a valid bool, an exception is thrown.

    Args:
      inputs (dict):  Key/value pairs of user inputs.
      field (str):  The field to get.

    Returns:
      bool: Returns None if field is not in inputs.  Otherwise the input
      field is converted to a boolean and returned.
    """
    value = inputs.pop(field, None)
    if value is None:
        return None

    if isinstance(value, str):
        lv = value.lower()
        if lv in ["true", 'on']:
            value = True
        elif lv in ["false", 'off']:
            value = False
        elif lv == 'none':
            return None

    try:
        # Use int() because bool("asdf") also returns true.  This ensures
        # only true/false or 1/0 is allowed.
        return bool(int(value))
    except ValueError:
        msg = "Invalid %s input.  Valid inputs are 1/0 or True/False" % input
        raise ValueError(msg)


#===========================================================================
def input_integer(inputs, field):
    """Convert an input field to an integer.

    Raises:
      If the input is not a valid integer, an exception is thrown.

    Args:
      inputs (dict):  Key/value pairs of user inputs.
      field (str): The field to get.

    Returns:
      Returns None if field is not in inputs.  Otherwise the input field
      is converted to an integer and returned.
    """
    value = inputs.pop(field, None)
    if value is None:
        return None

    try:
        if isinstance(value, str):
            lv = value.lower()
            if lv == 'none':
                return None

            if '0x' in value:
                return int(value, 16)
            elif '0b' in value:
                return int(value, 2)
            else:
                return int(value)
        else:
            return int(value)
    except ValueError:
        msg = "Invalid %s input.  Valid inputs are integer values." % input
        raise ValueError(msg)


#===========================================================================
def input_byte(inputs, field):
    """Convert an input field to a byte.

    Valid byte inputs are integers or strings leading with '0x' (base 16 hex
    value) or '0b' (base 2 binary value).

    Raises:
      If the input is not a valid byte, an exception is thrown.

    Args:
      inputs (dict):  Key/value pairs of user inputs.
      field (str):  The field to get.

    Returns:
      byte: Returns None if field is not in inputs.  Otherwise the input
      field is converted to a byte and returned.
    """
    value = inputs.pop(field, None)
    if value is None:
        return None

    try:
        if isinstance(value, str):
            if '0x' in value:
                v = int(value, 16)
            elif '0b' in value:
                v = int(value, 2)
            else:
                v = int(value)
        else:
            v = int(value)

        if v < 0 or v > 255:
            raise ValueError("Value out of range")

        return v
    except ValueError:
        msg = "Invalid %s input.  Valid inputs are 0-255" % input
        raise ValueError(msg)
