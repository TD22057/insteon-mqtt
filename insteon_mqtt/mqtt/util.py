#===========================================================================
#
# MQTT utilities
#
#===========================================================================
from .. import on_off
from .. import log


LOG = log.get_logger()


def parse_on_off(data, have_mode=True):
    """Parse on/off JSON data from an input message payload.

    The on/off flag is controlled by the data['cmd'] attribute which must be
    'on' or 'off'.

    The on/off mode is NORMAL by default.  It can be set by the optional
    field data['mode'] which can be 'normal', 'fast', 'instant', or 'ramp'.
    Or it can be set by the boolean fields data['fast'] or data['instant'].
    If a transition time is specified and fast/instant is not, then 'ramp' mode
    is used.

    Args:
      data (dict):  The message payload converted to a JSON dictionary.
      have_mode (bool):  If True, mode parsing is supported.  If False,
                the returned mode will always be None.

    Returns:
      (bool is_on, on_off.Mode, transition): Returns a boolean to indicate
         on/off, the requested on/off mode enumeration to use, and a transition
         time if present.  If have_mode is False, then only the is_on flag is
         returned.
    """
    # Parse the on/off command input.
    cmd = data.get('cmd').lower()
    if cmd == 'on':
        is_on = True
    elif cmd == 'off':
        is_on = False
    else:
        LOG.error("Invalid on/off command input '%s'", cmd)
        raise Exception("Invalid on/off command input '%s'" % cmd)

    if not have_mode:
        return is_on

    # If mode is present, use that to specify normal/fast/instant.
    # Otherwise look for individual keywords.
    if 'mode' in data:
        mode_str = data.get('mode')
        try:
            mode = on_off.Mode(mode_str.lower())
        except:
            LOG.error("Invalid mode command input '%s'", mode_str)
            mode = on_off.Mode.NORMAL
    else:
        mode = on_off.Mode.NORMAL
        if data.get('fast', False):
            mode = on_off.Mode.FAST
        elif data.get('instant', False):
            mode = on_off.Mode.INSTANT

    # Ramp mode is implied if transition is specified and fast/instant are not
    transition = data.get("transition", None)
    if (transition is not None) and (mode == on_off.Mode.NORMAL):
        mode = on_off.Mode.RAMP

    return is_on, mode, transition

#===========================================================================
