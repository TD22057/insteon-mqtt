#===========================================================================
#
# Set Functions.
#
#===========================================================================
from ..Base import Base
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
            'set' : self.set,
            })

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
    def on(self, group, level, mode, reason, transition, on_done):
        # TODO Might be able to move these functions in here too
        # Probably put switch functions here and dimmer in a seperate
        # level file.  Need to move handle_ack and all subsequent functions
        # too.  KPL, IO devices would remain their own thing
        raise NotImplementedError()

    #-----------------------------------------------------------------------
    def off(self, group, mode, reason, transition, on_done):
        raise NotImplementedError()
