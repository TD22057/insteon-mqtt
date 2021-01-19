#===========================================================================
#
# Scene Functions.  This enables the simulated scene function used on the
# Dimmer, Switch, and KeypadLinc.
#
#===========================================================================
import time
from ..Base import Base
from ... import handler
from ... import log
from ... import message as Msg
from ... import on_off
from ... import util

LOG = log.get_logger()


class Scene(Base):
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
            'scene' : self.scene,
            })

        # Special callback to run when receiving a broadcast clean up.  See
        # scene() for details.
        self.broadcast_reason = ""

        # NOTE!
        # The class extending this class needs to define the controller groups
        # in the self.group_map.  Only these groups will be valid scene
        # targets

    def scene(self, is_on, group=0x01, name=None, reason=None, level=None,
              on_done=None):
        """Trigger a scene on the device.

        Triggering a scene is the same as simulating a button press on the
        device.  It will change the state of the device and notify responders
        that are linked to the device to update their state as well.

        The process looks like:
          Modem -> Device OutExtended Scene Command
          Modem <- Device Device ACK
          World <- Device Broadcast
          Modem <- Device Direct Cleanup
          Modem <- Device Cleanup Report [Not always received]

        Args:
          is_on (bool): True for an on command, False for an off command.
          group (int): The group on the device to simulate.  For this device,
                this must be 1.
          name (None): Not used, only here for modem compatibility.
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          level (int):  Brightness level [0-255] to set the device to if
                 the device supports dimming.  Linked devices will always
                 turn on to the level specified in their link.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Device %s scene %s", self.addr, "on" if is_on else "off")
        if group is None:
            group = 0x01
        assert group in self.group_map

        if name is not None:
            LOG.error("Device %s scenes cannot use names, groups only.",
                      self.addr)

        on_done = util.make_callback(on_done)

        # Send an 0x30 all link command to simulate the button being pressed
        # on the switch.  See page 163 of insteon dev guide
        cmd1 = 0x11 if is_on else 0x13
        # Must specify use_on_level if cmd is off
        use_on_level = 0x00 if is_on else 0x01
        # Only used if use_on_level is 0x01, default 0x00 for Off cmd
        on_level = 0x00
        if level is not None:
            use_on_level = 0x01
            on_level = int(level)
        data = bytes([
            group,         # D1 = group (button)
            use_on_level,  # D2 = 0x00 use level in scene db or 0x01 use D3
            on_level,      # D3 = on level if D2=0x01
            cmd1,          # D4 = cmd1 to send to linked devices
            0x01,          # D5 = cmd2 to send
            0x00,          # D6 = use ramp rate in scene db or 0x01 for fast
            ] + [0x00] * 8)
        msg = Msg.OutExtended.direct(self.addr, 0x30, 0x00, data)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        def our_on_done(success, msg, data):
            if success:
                # We know that a broadcast command is going to arrive from the
                # device.  The amount of time we need to wait is unknown, but
                # this is a reasonable guess, that will be overwritten by the
                # wait time calculated by the arriving broadcast message.
                self.protocol.set_wait_time(time.time() + 1)
                # Reason is device because we're simulating a button press.
                # We can't really pass this around because we just get a
                # broadcast message later from the device.  So we set a
                # temporary variable here and use it in handle_broadcast()
                # to output the reason.
                if reason is not None:
                    self.broadcast_reason = reason
                else:
                    self.broadcast_reason = on_off.REASON_DEVICE
            on_done(success, msg, data)
        callback = self.generic_ack_callback("Device acknowledged scene cmd.")
        msg_handler = handler.StandardCmd(msg, callback, our_on_done)
        self.send(msg, msg_handler)
