#===========================================================================
#
# Dimmer Flag Functions.  Specifically Ramp_Rate and On_Level
#
#===========================================================================
import functools
from ..Base import Base
from ... import handler
from ... import log
from ... import message as Msg
from ... import util


LOG = log.get_logger()


class DimmerFlags(Base):
    """DimmerFlags Trait Abstract Class

    This is an abstract class that provides support for the ramp_rate and
    on_level flags found on dimmer devices.
    """
    # Mapping of ramp rates to human readable values
    ramp_pretty = {0x00: 540, 0x01: 480, 0x02: 420, 0x03: 360, 0x04: 300,
                   0x05: 270, 0x06: 240, 0x07: 210, 0x08: 180, 0x09: 150,
                   0x0a: 120, 0x0b: 90, 0x0c: 60, 0x0d: 47, 0x0e: 43, 0x0f: 39,
                   0x10: 34, 0x11: 32, 0x12: 30, 0x13: 28, 0x14: 26,
                   0x15: 23.5, 0x16: 21.5, 0x17: 19, 0x18: 8.5, 0x19: 6.5,
                   0x1a: 4.5, 0x1b: 2, 0x1c: .5, 0x1d: .3, 0x1e: .2, 0x1f: .1}

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
        self.set_flags_map.update({'on_level': self.set_on_level,
                                   'ramp_rate': self.set_ramp_rate})

    #-----------------------------------------------------------------------
    def set_on_level(self, on_done=None, **kwargs):
        """Set the device default on level.

        This changes the dimmer level the device will go to when the on
        button is pressed.  This can be very useful because a double-tap
        (fast-on) will the turn the device to full brightness if needed.

        Args:
          level (int): The default on level in the range [0,255]
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # Check for valid input
        level = util.input_byte(kwargs, 'on_level')
        if level is None:
            LOG.error("Invalid on level.")
            on_done(False, 'Invalid on level.', None)
            return

        LOG.info("Device %s setting on level to %s", self.label, level)

        # Extended message data - see Insteon dev guide p156.
        data = bytes([
            0x01,   # D1 must be group 0x01
            0x06,   # D2 set on level when button is pressed
            level,  # D3 brightness level
            ] + [0x00] * 11)

        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = functools.partial(self.handle_on_level, level=level)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_ramp_rate(self, on_done=None, **kwargs):
        """Set the device default ramp rate.

        This changes the dimmer default ramp rate of how quickly it will
        turn on or off. This rate can be between 0.1 seconds and up to 9
        minutes.

        Args:
          rate (float): Ramp rate in in the range [0.1, 540] seconds
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # Check for valid input
        rate = util.input_float(kwargs, 'ramp_rate')
        if rate is None:
            LOG.error("Invalid ramp rate.")
            on_done(False, 'Invalid ramp rate.', None)
            return

        LOG.info("Dimmer %s setting ramp rate to %s", self.label, rate)

        data_3 = 0x1c  # the default ramp rate is .5
        for ramp_key, ramp_value in self.ramp_pretty.items():
            if rate >= ramp_value:
                data_3 = ramp_key
                break

        # Extended message data - see Insteon dev guide p156.
        data = bytes([
            0x01,   # D1 must be group 0x01
            0x05,   # D2 set ramp rate when button is pressed
            data_3,  # D3 rate
            ] + [0x00] * 11)

        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = self.generic_ack_callback("Button ramp rate updated")
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_on_level(self, msg, on_done, level):
        """Callback for handling set_on_level() responses.

        This is called when we get a response to the set_on_level() command.
        Update stored on-level in device DB and call the on_done callback with
        the status.

        Args:
          msg (InpStandard): The response message from the command.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        self.db.set_meta('on_level', level)
        on_done(True, "Button on level updated", None)

    #-----------------------------------------------------------------------
    def get_on_level(self):
        """Look up previously-set on-level in device database, if present

        This is called when we need to look up what is the default on-level
        (such as when getting an ON broadcast message from the device).

        If on_level is not found in the DB, assumes on-level is full-on.
        """
        on_level = self.db.get_meta('on_level')
        if on_level is None:
            on_level = 0xff
        return on_level
