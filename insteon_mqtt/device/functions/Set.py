#===========================================================================
#
# Set Functions.
#
#===========================================================================
import functools
from ..Base import Base
from ... import message as Msg
from ... import handler
from ... import log
from ... import on_off


LOG = log.get_logger()


class Set(Base):
    """Scene Trait Abstract Class

    This is an abstract class that provides support for the Scene topic.
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
        LOG.info("Device %s cmd: on %s", self.addr, mode)
        assert group in self.responder_groups
        assert isinstance(mode, on_off.Mode)

        mode, transition = self.adjust_transition(mode, transition)
        mode, level = self.adjust_level(mode, level)

        # Send the requested on code value.
        cmd1 = on_off.Mode.encode(True, mode)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        msg = Msg.OutStandard.direct(self.addr, cmd1, level)
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
        LOG.info("Device %s cmd: off %s", self.addr, mode)
        assert group in self.responder_groups
        assert isinstance(mode, on_off.Mode)

        mode, transition = self.adjust_transition(mode, transition)

        # Send an off or instant off command.
        cmd1 = on_off.Mode.encode(False, mode)
        cmd2 = 0x00

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        msg = Msg.OutStandard.direct(self.addr, cmd1, cmd2)
        callback = functools.partial(self.handle_ack, reason=reason)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def adjust_transition(self, mode, transition):
        """Check whether device supports transition

        Adjusts mode and transition based on device support

        Args:
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          transition (int): Ramp rate for the transition in seconds.
        Returns
          mode (on_off.Mode): Adjusted mode based on device supports.
          transition (int): Adjusted transition based on device supports.
        """
        if transition:
            LOG.error("Device %s does not support transition.", self.addr)
            transition = None
        return (mode, transition)

    #-----------------------------------------------------------------------
    def adjust_level(self, mode, level):
        """Check whether device supports level

        Adjusts mode and level based on device support

        Args:
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
          level (int): On level between 0-255.
        Returns
          mode (on_off.Mode): Adjusted mode based on device supports.
          level (int): Adjusted on level based on device supports.  Always
                       returns 0xFF for default devices.
        """
        if level:
            LOG.error("Device %s does not support level.", self.addr)
        level = 0xFF
        return (mode, level)

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
        reason = reason if reason else on_off.REASON_COMMAND
        self._set_state(is_on=is_on, mode=mode, reason=reason)
        on_done(True, "Switch state updated to on=%s" % is_on, is_on)

    #-----------------------------------------------------------------------
    def _set_state(self, is_on=None, level=None, mode=on_off.Mode.NORMAL,
                   reason=""):
        raise NotImplementedError()
