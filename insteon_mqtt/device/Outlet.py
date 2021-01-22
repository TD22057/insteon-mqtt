#===========================================================================
#
# Insteon on/off outlet
#
#===========================================================================
import functools
from .base import ResponderBase
from .functions import Backlight
from ..CommandSeq import CommandSeq
from .. import handler
from .. import log
from .. import message as Msg
from .. import on_off

LOG = log.get_logger()


class Outlet(Backlight, ResponderBase):
    """Insteon on/off outlet device.

    This is used for in-wall on/off outlets.  Each outlet (top and bottom) is
    an independent switch and is controlled via group 1 (top) and group2
    (bottom) inputs.

    State changes are communicated by emitting signals.  Other classes can
    connect to these signals to perform an action when a change is made to
    the device (like sending MQTT messages).
    """

    def __init__(self, protocol, modem, address, name=None):
        """Constructor

        Args:
          protocol (Protocol):  The Protocol object used to communicate
                   with the Insteon network.  This is needed to allow the
                   device to send messages to the PLM modem.
          modem (Modem):  The Insteon modem used to find other devices.
          address (Address):  The address of the device.
          name (str):  Nice alias name to use for the device.
        """
        super().__init__(protocol, modem, address, name)

        self._is_on = [False, False]  # top outlet, bottom outlet

        # NOTE: the outlet does NOT include the group in the ACK of an on/off
        # command.  So there is no way to tell which outlet is being ACK'ed
        # if we send multiple messages to it.  Each time on or off is called,
        # it pushes the outlet to this list so that when the ACK/NAK arrives,
        # we can pop it off and know which outlet was being commanded.
        self._which_outlet = []

        # Update the group map with the groups to be paired and the handler
        # for broadcast messages from this group
        # Can the outlet really act as a controller?
        self.group_map.update({0x01: self.handle_on_off,
                               0x02: self.handle_on_off})

        # List of responder group numbers
        self.responder_groups = [0x01, 0x02]

    #-----------------------------------------------------------------------
    def refresh(self, force=False, on_done=None):
        """Refresh the current device state and database if needed.

        This sends a ping to the device.  The reply has the current device
        state (on/off, level, etc) and the current db delta value which is
        checked against the current db value.  If the current db is out of
        date, it will trigger a download of the database.

        This will send out an updated signal for the current device status
        whenever possible (like dimmer levels).

        Args:
          force (bool):  If true, will force a refresh of the device database
                even if the delta value matches as well as a re-query of the
                device model information even if it is already known.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Outlet %s cmd: status refresh", self.label)

        seq = CommandSeq(self, "Device refreshed", on_done, name="DevRefresh")

        # This sends a refresh ping which will respond w/ the current
        # database delta field.  The handler checks that against the current
        # value.  If it's different, it will send a database download command
        # to the device to update the database.  Code 0x19 also allows us to
        # get the state of both outlets in a single field.
        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x01)
        msg_handler = handler.DeviceRefresh(self, self.handle_refresh, force,
                                            on_done, num_retry=3)
        seq.add_msg(msg, msg_handler)

        # If model number is not known, or force true, run get_model
        self.addRefreshData(seq, force)

        # Run all the commands.
        seq.run()

    #-----------------------------------------------------------------------
    def on(self, group=0x01, level=None, mode=on_off.Mode.NORMAL,
           reason="", transition=None, on_done=None):
        """Turn the device on.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          group (int):  The group to send the command to.  The top outlet is
                group 1, the bottom outlet is group 2.
          level (int):  If non zero, turn the device on.  Should be in the
                range 0 to 255.  Only dimmers use the intermediate values, all
                other devices look at level=0 or level>0.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # See __init__ code comments for what this is for.
        self._which_outlet.append(group)

        # Bottom outlet uses an extended message
        if group == 2:
            cmd1, cmd2 = self.cmd_on_values(mode, level, transition, group)
            data = bytes([0x02] + [0x00] * 13)
            msg = Msg.OutExtended.direct(self.addr, cmd1, cmd2, data)
            callback = functools.partial(self.handle_ack, reason=reason)
            msg_handler = handler.StandardCmd(msg, callback, on_done)
            self.send(msg, msg_handler)
        else:
            # Top outlet uses a regular on command pass to SetAndState
            super().on(group=group, level=level, mode=mode, reason=reason,
                       transition=transition, on_done=on_done)

    #-----------------------------------------------------------------------
    def off(self, group=0x01, mode=on_off.Mode.NORMAL, reason="",
            transition=None, on_done=None):
        """Turn the device off.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          group (int):  The group to send the command to.  The top outlet is
                group 1, the bottom outlet is group 2.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # See __init__ code comments for what this is for.
        self._which_outlet.append(group)

        # Bottom outlet uses an extended message
        if group == 2:
            cmd1, cmd2 = self.cmd_off_values(mode, transition, group)
            data = bytes([0x02] + [0x00] * 13)
            msg = Msg.OutExtended.direct(self.addr, cmd1, cmd2, data)
            callback = functools.partial(self.handle_ack, reason=reason)
            msg_handler = handler.StandardCmd(msg, callback, on_done)
            self.send(msg, msg_handler)
        else:
            # Top outlet uses a regular on command pass to SetAndState
            super().off(group=group, mode=mode, reason=reason,
                        transition=transition, on_done=on_done)

    #-----------------------------------------------------------------------
    def handle_refresh(self, msg, group=None):
        """Callback for handling refresh() responses.

        This is called when we get a response to the refresh() command.  The
        refresh command reply will contain the current device state in cmd2
        and this updates the device with that value.  It is called by
        handler.DeviceRefresh when we can an ACK for the refresh command.

        Args:
          msg (message.InpStandard):  The refresh message reply.  The current
              device state is in the msg.cmd2 field.
        """
        # From outlet developers guide - refresh must be 0x19 0x01 to enable
        # these codes which allows us to get the state of both outlets with
        # one call.
        response = {
            0x00: [False, False],
            0x01: [True, False],
            0x02: [False, True],
            0x03: [True, True]
            }

        is_on = response.get(msg.cmd2, None)
        if is_on is not None:
            LOG.ui(" %s refresh top=%s bottom=%s", self.label, is_on[0],
                   is_on[1])

            # Set the state for each outlet.
            self._set_state(group=1, is_on=is_on[0],
                            reason=on_off.REASON_REFRESH)
            self._set_state(group=2, is_on=is_on[1],
                            reason=on_off.REASON_REFRESH)

        else:
            LOG.error("Outlet %s unknown refresh response %s", self.label,
                      msg.cmd2)

    #-----------------------------------------------------------------------
    def decode_on_level(self, cmd1, cmd2):
        """Callback for standard commanded messages.

        Decodes the cmds recevied from the device into is_on, level, and mode
        to be consumed by _set_state().

        Args:
          cmd1 (byte): The command 1 value
          cmd2 (byte): The command 2 value
        Returns:
          is_on (bool): Is the device on.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          level (int): On level between 0-255.
          group (int): The group number that this state applies to. Defaults
                       to None.
        """
        # Default Returns
        group = None
        is_on = None
        level = None
        mode = on_off.Mode.NORMAL

        # Get the last outlet we were commanding.  The message doesn't tell
        # us which outlet it was so we have to track it here.  See __init__
        # code comments for more info.
        if not self._which_outlet:
            LOG.error("Outlet %s ACK error.  No outlet ID's were saved",
                      self.addr)
        else:
            group = self._which_outlet.pop(0)
            is_on, mode = on_off.Mode.decode(cmd1)
        return (is_on, level, mode, group)

    #-----------------------------------------------------------------------
    def group_cmd_local_group(self, entry):
        """Get the Local Group Affected by this Group Command

        For most devices this is group 1, but for multigroup devices such
        as the KPL, they may need to decode the local group from the
        entry data.

        Args:
          entry (DeviceEntry):  The local db entry for this group command.
        Returns:
          group (int):  The local group affected
        """
        return entry.data[2]

    #-----------------------------------------------------------------------
    def _cache_state(self, group, is_on, level, reason):
        """Cache the State of the Device

        Used to help with the unique device functions.

        Args:
          group (int): The group which this applies
          is_on (bool): Whether the device is on.
          level (int): The new device level in the range [0,255].  0 is off.
          reason (str): Reason string to pass around.
        """
        self._is_on[group - 1] = is_on

    #-----------------------------------------------------------------------
