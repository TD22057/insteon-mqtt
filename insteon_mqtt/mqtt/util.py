#===========================================================================
#
# MQTT utilities
#
#===========================================================================
from .. import on_off


def parse_on_off(data, have_mode=True):
    """Parse on/off JSON data from an input message payload.

    The on/off flag is controlled by the data['cmd'] attribute which must be
    'on' or 'off'.

    The on/off mode is NORMAL by default.  It can be set by the optional
    field data['mode'] which can be 'normal', 'fast', or 'instant'.  Or it
    can be set by the boolean fields data['fast'] or data['instant'].

    Args:
      data (dict):  The message payload converted to a JSON dictionary.
      have_mode (bool):  If True, mode parsing is supported.  If False,
                the returned mode will always be None.

    Returns:
      (bool is_on, on_off.Mode): Returns a boolean to indicate on/off and the
         requested on/off mode enumeration to use.  If have_mode is False,
         then only the is_on flag is returned.
    """
    # Parse the on/off command input.
    cmd = data.get('cmd').lower()
    if cmd == 'on':
        is_on = True
    elif cmd == 'off':
        is_on = False
    else:
        raise Exception("Invalid on/off command input '%s'" % cmd)

    if not have_mode:
        return is_on

    # If mode is present, use that to specify normal/fast/instant.
    # Otherwise look for individual keywords.
    if 'mode' in data:
        mode = on_off.Mode(data.get('mode', 'normal').lower())
    else:
        mode = on_off.Mode.NORMAL
        if data.get('fast', False):
            mode = on_off.Mode.FAST
        elif data.get('instant', False):
            mode = on_off.Mode.INSTANT

    return is_on, mode

#===========================================================================
