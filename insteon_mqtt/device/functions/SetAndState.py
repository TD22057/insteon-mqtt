#===========================================================================
#
# Provides BOTH the Set and State Functions.
#
#===========================================================================
import functools
from ..Base import Base
from ... import message as Msg
from ... import handler
from ... import log
from ... import on_off
from .State import State


LOG = log.get_logger()


class SetAndState(State):
    """Set and State Abstract Classes

    This is an abstract class that provides support for the set and state
    functions.  A device SHOULD NOT also inherit from the State function if
    it is using this.  Some devices BatterSensor may only inherit from State.
    """
    def __init__(self, protocol, modem, address, name=None):
        """Constructor

        Args:
          protocol (Protocol): The Protocol object used to communicate
                   with the Insteon network.  This is needed to allow the
                   device to send messages to the PLM modem.
          modem (Modem): The Insteon modem used to find other devices.
          address (Address): The address of the device.
          name (str): Nice alias name to use for the device.
        """
        super().__init__(protocol, modem, address, name)

        self.cmd_map.update({
            'on' : self.on,
            'off' : self.off,
            'set' : self.set,
            })

        # List of responder group numbers
        self.responder_groups = [0x01]

    #-----------------------------------------------------------------------
    def set(self, is_on=None, level=None, group=0x01, mode=on_off.Mode.NORMAL,
            reason="", transition=None, on_done=None):
        """Turn the device on or off.  Level zero will be off.

        NOTE: This does NOT simulate a button press on the device - it just
        changes the state of the device.  It will not trigger any responders
        that are linked to this device.  To simulate a button press, call the
        scene() method.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          is_on (bool): True to turn on, False for off
          level (int): If non zero, turn the device on.  Should be in the
                range 0 to 255.  If None, use default on-level.
          group (int): The group to send the command to.  For this device,
                this must be 1.  Allowing a group here gives us a consistent
                API to the on command across devices.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          transition (int): The transition ramp_rate if supported.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        if is_on or level:
            self.on(group=group, level=level, mode=mode, reason=reason,
                    transition=transition, on_done=on_done)
        else:
            self.off(group=group, mode=mode, reason=reason,
                     transition=transition, on_done=on_done)

    #-----------------------------------------------------------------------
    def on(self, group=0x01, level=None, mode=on_off.Mode.NORMAL, reason="",
           transition=None, on_done=None):
        """Turn the device on.

        NOTE: This does NOT simulate a button press on the device - it just
        changes the state of the device.  It will not trigger any responders
        that are linked to this device.  To simulate a button press, call the
        scene() method.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          group (int):  The group to send the command to.
          level (int):  If non-zero, turn the device on.  The API is an int
                to keep a consistent API with other devices.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        group = self.adjust_set_group(group)

        LOG.info("Device %s grp: %s cmd: on %s", self.addr, group, mode)
        assert group in self.responder_groups
        assert isinstance(mode, on_off.Mode)

        if self.use_alt_set_cmd(group, True, reason, on_done):
            return

        # Send the requested on code value.
        cmd1, cmd2 = self.cmd_on_values(mode, level, transition)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        msg = Msg.OutStandard.direct(self.addr, cmd1, cmd2)
        callback = functools.partial(self.handle_ack, reason=reason)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def off(self, group=0x01, mode=on_off.Mode.NORMAL, reason="",
            transition=None, on_done=None):
        """Turn the device off.

        NOTE: This does NOT simulate a button press on the device - it just
        changes the state of the device.  It will not trigger any responders
        that are linked to this device.  To simulate a button press, call the
        scene() method.

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          group (int):  The group to send the command to.
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        group = self.adjust_set_group(group)

        LOG.info("Device %s grp: %s cmd: off %s", self.addr, group, mode)
        assert group in self.responder_groups
        assert isinstance(mode, on_off.Mode)

        if self.use_alt_set_cmd(group, False, reason, on_done):
            return

        # Send an off or instant off command.
        cmd1, cmd2 = self.cmd_off_values(mode, transition)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        msg = Msg.OutStandard.direct(self.addr, cmd1, cmd2)
        callback = functools.partial(self.handle_ack, reason=reason)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def cmd_on_values(self, mode, level, transition):
        """Calculate Cmd Values for On

        Args:
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          level (int): On level between 0-255.
          transition (int): Ramp rate for the transition in seconds.
        Returns
          cmd1, cmd2 (int): Value of cmds for this device.
        """
        if transition:
            LOG.error("Device %s does not support transition.", self.addr)
        if level:
            LOG.error("Device %s does not support level.", self.addr)
        cmd1 = on_off.Mode.encode(True, mode)
        cmd2 = 0xFF
        return (cmd1, cmd2)

    #-----------------------------------------------------------------------
    def cmd_off_values(self, mode, transition):
        """Calculate Cmd Values for Off

        Args:
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          transition (int): Ramp rate for the transition in seconds.
        Returns
          cmd1, cmd2 (int): Value of cmds for this device.
        """
        if transition:
            LOG.error("Device %s does not support transition.", self.addr)
        cmd1 = on_off.Mode.encode(False, mode)
        cmd2 = 0x00
        return (cmd1, cmd2)

    #-----------------------------------------------------------------------
    def use_alt_set_cmd(self, group, is_on, reason, on_done):
        """Should this be processed using an alternate command?

        Exists for the KPL to intercept on/off commands for the non-load group.
        If should process using an alternate command, do that here and return
        True.

        Args:
          group (int): The group the command should be sent to.
          is_on (bool): Should the command be on?
          reason (str): The reason string
          on_done (callback): The on_done callback.
        Returns
          True if the command has been processed elsewhere, False otherwise.
        """
        return False

    #-----------------------------------------------------------------------
    def adjust_set_group(self, group):
        """Adjust the group number for processing by the set command?

        Exists for the KPL to alter the group number based on the load_group

        Args:
          group (int): The group the command should be sent to.
        Returns
          Group(int): The adjusted group number.
        """
        return group

    #-----------------------------------------------------------------------
    def handle_ack(self, msg, on_done, reason=""):
        """Callback for standard commanded messages.

        This callback is run when we get a reply back from one of our
        commands to the device.  If the command was ACK'ed, we know it worked
        so we'll update the internal state of the device and emit the signals
        to notify others of the state change.

        Args:
          msg (message.InpStandard):  The reply message from the device.
              The on/off level will be in the cmd2 field.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
        """
        # If this it the ACK we're expecting, update the internal state and
        # emit our signals.
        LOG.debug("Device %s ACK: %s", self.addr, msg)

        is_on, mode = on_off.Mode.decode(msg.cmd1)
        level = on_off.Mode.decode_level(msg.cmd1, msg.cmd2)
        reason = reason if reason else on_off.REASON_COMMAND
        self._set_state(is_on=is_on, level=level, mode=mode, reason=reason)
        on_done(True, "Device state updated to on=%s" % is_on, is_on)
