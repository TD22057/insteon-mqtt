#===========================================================================
#
# DimmerBase Class.  Specifically Resume_Dim, Ramp_Rate and On_Level Flags,
# increment_up and increment_down functions.  Extensions to ManualCtrl
# Plus other dimmer helper functions
#
# NOTE! This is a meta class that include Responder and ManualCtrl. DO NOT
# inherit from these classes if you are using this Meta class.
#
#===========================================================================
import functools
import time
from .ResponderBase import ResponderBase
from .Base import Base
from ..functions import ManualCtrl
from ... import handler
from ... import log
from ... import message as Msg
from ... import util
from ... import on_off


LOG = log.get_logger()


class DimmerBase(ManualCtrl, ResponderBase, Base):
    """Dimmer Functions Trait Abstract Class

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

    def __init__(self, protocol, modem, address, name=None, config_extra=None):
        """Constructor

        Args:
          protocol (Protocol): The Protocol object used to communicate
                   with the Insteon network.  This is needed to allow the
                   device to send messages to the PLM modem.
          modem (Modem): The Insteon modem used to find other devices.
          address (Address): The address of the device.
          name (str): Nice alias name to use for the device.
          config_extra (dict): Extra configuration settings
        """
        super().__init__(protocol, modem, address, name, config_extra)

        # Remote (mqtt) commands mapped to methods calls.  Add to the base
        # class defined commands.
        self.cmd_map.update({
            'increment_up' : self.increment_up,
            'increment_down' : self.increment_down,
            })

        # Define the flags handled by set_flags()
        self.set_flags_map.update({'on_level': self.set_on_level,
                                   'ramp_rate': self.set_ramp_rate,
                                   'resume_dim': self.set_resume_dim})

    #========= Flags Functions
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
          ramp_rate (float): Ramp rate in in the range [0.1, 540] seconds
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        # Check for valid input
        rate = util.input_float(kwargs, 'ramp_rate')
        if rate is None:
            LOG.error("Invalid ramp rate.")
            on_done(False, 'Invalid ramp rate.', None)
            return

        LOG.info("Device %s setting ramp rate to %s", self.label, rate)

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

    def set_resume_dim(self, on_done=None, **kwargs):
        """Set the device resume dim operating flag on/off

        This enables or disabled the resume dim level functionality
        and is used in conjuction with the configured on level to determine
        the default on level for 'normal' speeds.  If this is enabled, the
        device will resume it's previous level when turned on; otherwise
        it will return to the configured on level.  This can be very useful
        because a double-tap (fast-on) will the turn the device to full
        brightness if needed.

        Args:
          resume_dim (bool): resume dim is enabled
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        resume_dim = util.input_bool(kwargs, 'resume_dim')

        # These values were pulled from the insteon command tables pdf
        # page 8
        # 0x04 - Enables resume dim
        # 0x05 - Disables resume dim
        if resume_dim:
            LOG.info("Device %s enabling resume dim", self.label)
            msg = self._set_operating_flag_msg(0x04)
        else:
            LOG.info("Device %s disabling resume dim", self.label)
            msg = self._set_operating_flag_msg(0x05)

        # Use the standard command handler which will notify us when the
        # command is ACK'ed.
        callback = self.generic_ack_callback("Button resume dim updated")
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

    #========= Increment Functions
    #-----------------------------------------------------------------------
    def increment_up(self, reason="", on_done=None):
        """Increment the current level up.

        Levels increment in units of 8 (32 divisions from off to on).

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Device %s cmd: increment up", self.addr)

        msg = Msg.OutStandard.direct(self.addr, 0x15, 0x00)

        callback = functools.partial(self.handle_increment, delta=+8,
                                     reason=reason)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def increment_down(self, reason="", on_done=None):
        """Increment the current level down.

        Levels increment in units of 8 (32 divisions from off to on).

        This will send the command to the device to update it's state.  When
        we get an ACK of the result, we'll change our internal state and emit
        the state changed signals.

        Args:
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Device %s cmd: increment down", self.addr)

        msg = Msg.OutStandard.direct(self.addr, 0x16, 0x00)

        callback = functools.partial(self.handle_increment, delta=-8,
                                     reason=reason)
        msg_handler = handler.StandardCmd(msg, callback, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_increment(self, msg, on_done, delta, reason="", group=0x01):
        """Callback for increment up/down commanded messages.

        This callback is run when we get a reply back from triggering an
        increment up or down on the device.  If the command was ACK'ed, we
        know it worked.

        Args:
          msg (message.InpStandard): The reply message from the device.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)

          delta (int):  The amount +/- of level to change by.
          reason (str):  This is optional and is used to identify why the
                 command was sent. It is passed through to the output signal
                 when the state changes - nothing else is done with it.
        """
        # If this it the ACK we're expecting, update the internal state and
        # emit our signals.
        LOG.debug("Device %s ACK: %s", self.addr, msg)

        # Add the delta and bound at [0, 255]
        level = min(self._level + delta, 255)
        level = max(level, 0)
        self._set_state(group=group, level=level, reason=reason)

        s = "Device %s state updated to %s" % (self.addr, self._level)
        on_done(True, s, msg.cmd2)

    #========= Helper Functions
    #-----------------------------------------------------------------------
    def derive_on_level(self, mode):
        """Calculates the device on level based on the mode and the local
        on_level set in the flags.

        When a device is turned on using the physical button it will go to the
        on_level defined in its flags, unless it was a FAST on or the device
        was already on and was activated again in those cases it always goes to
        level 0xFF.

        Args:
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
        Returns:
          level (int)
        """
        if mode == on_off.Mode.FAST:
            # Fast-ON command.  Use full-brightness.
            level = 0xff
        else:
            # Normal/instant ON command.  Use default on-level.
            # Check if we saved the default on-level in the device
            # database when setting it.
            level = self.get_on_level()
            if self._level == level:
                # Pressing on again when already at the default on
                # level causes the device to go to full-brightness.
                level = 0xff

            # If on was set using a scene command in the last 5 seconds, then
            # set to level requested in the scene command
            if self.broadcast_scene_level['timestamp'] + 5 >= time.time():
                level = self.broadcast_scene_level['level']

            # No matter what, clear the scene level
            self.broadcast_scene_level['timestamp'] = 0
        return level

    #-----------------------------------------------------------------------
    def derive_off_level(self, mode):
        """Calculates the device off level based on the mode and the local
        on_level set in the flags.

        This always returns 0x00 for dimmer devices.  By setting the level to
        not None, this will cause the mqtt template_data to produce variables
        based on the level data.  This may be a bit silly, but keeps things
        compatible with how it previously worked.

        Args:
          mode (on_off.Mode): The type of command to send (normal, fast, etc).
        Returns:
          level (int)
        """
        level = 0x00
        return level

    #-----------------------------------------------------------------------
    def group_cmd_on_level(self, entry, is_on):
        """Get the On Level for this Group Command

        For switches, this always returns None as this forces template_data
        in the MQTT classes to render without level data to comply with prior
        versions. But dimmers allow for the local on_level to be user defined
        and stored in the db entry.

        Args:
          entry (DeviceEntry):  The local db entry for this group command.
          is_on (bool): Whether the command was ON or OFF
        Returns:
          level (int):  The on_level or None
        """
        level = entry.data[0] if is_on else 0x00
        return level

    #-----------------------------------------------------------------------
    def group_cmd_handle_increment(self, cmd, group, reason):
        """Process Increment Group Commands

        This should do whatever processing is necessary, including updating
        the local state in response to an increment group command.  For non
        dimmable devices this does nothing.

        Args:
          cmd (Msg.CmdType): The cmd1 value of the message
          group (int):  The local db entry for this group command.
          reason (str): Whether the command was ON or OFF
        """
        # Increment up 1 unit which is 8 levels.
        if cmd == Msg.CmdType.BRIGHT:
            self._set_state(group=group, level=min(0xff, self._level + 8),
                            reason=reason)

        # Increment down 1 unit which is 8 levels.
        elif cmd == Msg.CmdType.DIM:
            self._set_state(group=group, level=max(0x00, self._level - 8),
                            reason=reason)

    #-----------------------------------------------------------------------
    def group_cmd_handle_manual(self, manual, group, reason):
        """Process Manual Group Commands

        This should do whatever processing is necessary, including updating
        the local state in response to a manual group command.  For non
        dimmable devices this does nothing.

        Args:
          manual (on_off.Manual): The manual mode
          group (int):  The local db entry for this group command.
          reason (str): Whether the command was ON or OFF
        """
        self.signal_manual.emit(self, button=group, manual=manual,
                                reason=reason)

        # If the button is released, refresh to get the final level.
        if manual == on_off.Manual.STOP:
            self.refresh()

    #-----------------------------------------------------------------------
    def handle_refresh(self, msg, group=None):
        """Callback for handling refresh() responses.

        This is called when we get a response to the refresh() command.  The
        refresh command reply will contain the current device state in cmd2
        and this updates the device with that value.  It is called by
        handler.DeviceRefresh when we can an ACK for the refresh command.

        Overrides Base.handle_refresh in order to add the level key to
        _set_state().

        Args:
          msg (message.InpStandard): The refresh message reply.  The current
              device state is in the msg.cmd2 field.
        """
        LOG.ui("Device %s refresh cmd2 %s", self.addr, msg.cmd2)

        # Level works for most things can add a derive state if needed.
        self._set_state(level=msg.cmd2, group=group,
                        reason=on_off.REASON_REFRESH)

    #========= Manual Functions
    #-----------------------------------------------------------------------
    def react_to_manual(self, manual, group, reason):
        """React to Manual Mode Received from the Device

        Non-dimmable devices react immediatly when issueing a manual command
        while dimmable devices slowly ramp on. This function is here to
        provide DimmerBase a place to alter the default functionality. This
        function should call _set_state() at the appropriate times to update
        the state of the device.

        Args:
          manual (on_off.Manual):  The manual command type
          group (int):  The group sending the command
          reason (str):  The reason string to pass on
        """
        # Refresh to get the new level after the button is released.
        # do nothing on UP and DOWN
        if manual == on_off.Manual.STOP:
            self.refresh()
