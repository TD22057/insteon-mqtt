#===========================================================================
#
# Backlight Functions.
#
#===========================================================================
from ..Base import Base
from ... import handler
from ... import log
from ... import message as Msg
from ... import util
from ...CommandSeq import CommandSeq


LOG = log.get_logger()


class Backlight(Base):
    """Backlight Trait Abstract Class

    This is an abstract class that provides support for controlling the
    backlight on devices.
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

        # Define the flags handled by set_flags()
        self.set_flags_map.update({'backlight': self.set_backlight})

    #-----------------------------------------------------------------------
    def set_backlight(self, on_done=None, **kwargs):
        """Set the device backlight level.

        This changes the level of the LED back light that is used by the
        device status LED's (dimmer levels, KeypadLinc buttons, etc).

        The default factory level is 0x1f.

        Per page 157 of insteon dev guide range is between 0x11 and 0x7F,
        however in practice backlight can be incremented from 0x00 to at least
        0x7f.

        Args:
          level (int):  The backlight level in the range [0,255]
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # Check for valid input
        level = util.input_byte(kwargs, 'backlight')
        if level is None:
            LOG.error("Invalid backlight level.")
            on_done(False, 'Invalid backlight level.', None)
            return

        seq = CommandSeq(self, "Device set backlight complete", on_done,
                         name="SetBacklight")

        # First set the backlight on or off depending on level value
        is_on = level > 0
        LOG.info("Device %s setting backlight to %s", self.label, is_on)
        cmd = 0x09 if is_on else 0x08
        msg = Msg.OutExtended.direct(self.addr, 0x20, cmd, bytes([0x00] * 14))
        callback = self.generic_ack_callback("Backlight set on: %s" % is_on)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        seq.add_msg(msg, msg_handler)

        if is_on:
            # Second set the level only if on
            LOG.info("Device %s setting backlight to %s", self.label, level)

            # Extended message data - see Insteon dev guide p156.
            data = bytes([
                0x01,   # D1 must be group 0x01
                0x07,   # D2 set global led brightness
                level,  # D3 brightness level
                ] + [0x00] * 11)

            msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)
            callback = self.generic_ack_callback("Backlight level updated")
            msg_handler = handler.StandardCmd(msg, callback, on_done)
            seq.add_msg(msg, msg_handler)

        seq.run()
