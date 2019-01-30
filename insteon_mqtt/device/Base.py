#===========================================================================
#
# Base device class
#
#===========================================================================
import json
import os.path
from .MsgHistory import MsgHistory
from ..Address import Address
from ..CommandSeq import CommandSeq
from .. import db
from .. import handler
from .. import log
from .. import message as Msg
from .. import util

LOG = log.get_logger()


class Base:
    """Base class for all Insteon devices.

    This class implements the required API for all devices and handles
    functions that are the same for all devices.

    The run_command() method is used for arbitrary remote commanding
    (via MQTT for example).  The input is a dict (or keyword args)
    containing a 'cmd' key with the value as the command name and any
    additional arguments needed for the command as other key/value
    pairs. Valid commands for all devices are:

       getdb:    No arguments.  Download the PLM modem all link database
                 and save it to file.
       refresh:  No arguments.  Ping the device and see if the database is
                 current.  Reloads the modem database if needed.
    """
    @classmethod
    def from_config(cls, values, protocol, modem, **kwargs):
        """TODO: doc
        """
        devices = []
        for config in values:
            # If it's a dict, it's got a nice name set.
            if isinstance(config, dict):
                assert len(config) == 1
                addr, name = next(iter(config.items()))
                name = name.lower()

            # Otherwise it's just the address
            else:
                addr = config
                name = None

            # Create the device using the class constructor.  Use kwargs
            # syntax so any extra keyword args don't have to be at the end of
            # the arg list.
            device = cls(protocol=protocol, modem=modem, address=addr,
                         name=name, **kwargs)
            devices.append(device)

        return devices

    #-----------------------------------------------------------------------
    def __init__(self, protocol, modem, address, name=None):
        """Constructor

        Args:
          protocol:    (Protocol) The Protocol object used to communicate
                       with the Insteon network.  This is needed to allow
                       the device to send messages to the PLM modem.
          modem:       (Modem) The Insteon modem used to find other devices.
          address:     (Address) The address of the device.
          name         (str) Nice alias name to use for the device.
        """
        self.protocol = protocol
        self.modem = modem
        self.addr = Address(address)
        self.name = name

        # Moving window history of messages that are received from the
        # device.  Used for optimal hop computations.
        self.history = MsgHistory()

        # Make some nice labels to make logging easier.
        self.label = str(self.addr)
        if self.name:
            self.label += " (%s)" % self.name

        self.save_path = modem.save_path
        self.db = db.Device(self.addr)
        self.load_db()

        # Remove (mqtt) commands mapped to methods calls.  These are
        # handled in run_command().  Derived classes can add more
        # commands to the dict to expand the list.  Commands should
        # all be lower case (inputs are lowered).
        self.cmd_map = {
            'db_add_ctrl_of' : self.db_add_ctrl_of,
            'db_add_resp_of' : self.db_add_resp_of,
            'db_del_ctrl_of' : self.db_del_ctrl_of,
            'db_del_resp_of' : self.db_del_resp_of,
            'print_db' : self.print_db,
            'refresh' : self.refresh,
            'linking' : self.linking,
            'join': self.join,
            'pair' : self.pair,
            'get_flags' : self.get_flags,
            'get_engine' : self.get_engine,
            'get_model' : self.get_model
            }

        # Device database delta.  The delta tells us if the database
        # is current.  The only way to get this is by sending a
        # refresh message out and getting the response - not by
        # downloading the database.
        self._next_db_delta = None

    #-----------------------------------------------------------------------
    def type(self):
        """Return a nice class name for the device.
        """
        if hasattr(self, "type_name"):
            return getattr(self, "type_name")

        return self.__class__.__name__.lower()

    #-----------------------------------------------------------------------
    def info_entry(self):
        """Return a JSON dictionary containing information about the device.
        """
        return {str(self.addr) : {
            "type" : self.type(),
            "label" : self.name,
            }}

    #-----------------------------------------------------------------------
    def send(self, msg, msg_handler, high_priority=False, after=None):
        """Send a message to the device.

        This will use the history of messages received from the device to set
        the number of hops to use in the message.

        Args:
          msg:            Output message to write.  This should be an
                          instance of a message in the message directory that
                          that starts with 'Out'.
          msg_handler:    Message handler instance to use when replies to the
                          message are received.  Any message received after we
                          write out the msg are passed to this handler until
                          the handler returns the message.FINISHED flags.
          high_priority:  (bool)False to add the message at the end of the
                          queue.  True to insert this message at the start of
                          the queue.
          after:          (float) Unix clock time tag to send the message
                          after. If None, the message is sent as soon as
                          possible.  Exact time is not guaranteed - the
                          message will be send no earlier than this.
        """
        if isinstance(msg, Msg.OutStandard):  # handles OutExtended as well
            msg.flags.set_hops(self.history.avg_hops())

        self.protocol.send(msg, msg_handler, high_priority, after)

    #-----------------------------------------------------------------------
    def db_path(self):
        """Return the all link database path.

        This will be the configuration save_path directory and the
        file name will be the modem hex address with a .json suffix.
        """
        return os.path.join(self.save_path, self.addr.hex) + ".json"

    #-----------------------------------------------------------------------
    def load_db(self):
        """Load the all link database from a file.

        The file is stored in JSON format (by save_db()) and has the
        path self.db_path().  If the file doesn't exist, nothing is
        done.
        """
        # TODO: fix this - kind of backward - should just set this into the
        # db and have it load itself.

        # See if the database file exists.
        path = self.db_path()
        self.db.set_path(path)
        if not os.path.exists(path):
            LOG.debug("Device %s db doesn't exist", self.label)
            return

        try:
            LOG.debug("Device %s reading db file", self.label)
            with open(path) as f:
                data = json.load(f)

            self.db = db.Device.from_json(data, path)
        except:
            LOG.exception("Error reading file %s", path)
            return

        LOG.info("Device %s database loaded %s entries", self.label,
                 len(self.db))
        LOG.debug("%s", self.db)

    #-----------------------------------------------------------------------
    def print_db(self, on_done):
        """Print the device database to the log UI.
        """
        LOG.ui("%s device database", self.label)
        LOG.ui("%s", self.db)
        on_done(True, "Complete", None)

    #-----------------------------------------------------------------------
    def join(self, on_done=None):
        """Joins the Device to the Modem, Enabling Communication

        Creates the Modem->Device Link that is Necessary for I2CS Devices.

        I2CS devices (Nearly all Insteon devices made since ~2012) will not
        respond to most messages sent to them unless they have a responder
        entry in their db for the device communicating with them.  Older
        devices that use I1 or I2 protocols do not have this limitation.

        This command can be run on any device version.  It will first check
        the engine version and then perform any steps necessary after that
        using the join_seq function.
        """
        LOG.info("Join Device %s", self.addr)

        # Using a sequence so we can pass the on_done function through.
        seq = CommandSeq(self.protocol, "Operation Complete", on_done)

        # Get Engine Version.  This process only works and is necessary on
        # I2CS devices.
        seq.add(self.get_engine)

        # Then run join_seq which checks to see if anything further is needed
        seq.add(self.join_seq)

        seq.run()

    #-----------------------------------------------------------------------
    def join_seq(self, on_done=None):
        """Join Sequence Called By Join Command

        This command is only required for I2CS devices.  This function is
        called after get_engine and will only perform a link sequence if
        the engine version requires it.
        """
        if self.db.engine < 0x02:
            on_done = util.make_callback(on_done)
            LOG.info("Device %s is not I2CS, join is unnecessary.", self.addr)
            on_done(True, "Operation Complete.", None)
            return
        else:
            # Build a sequence of calls to do the link.
            seq = CommandSeq(self.protocol, "Operation Complete", on_done)

            # Put Modem in linking mode first
            seq.add(self.modem.linking)

            # Now put this device in linking mode
            seq.add(self.linking)

            # Finally start the sequence running.
            seq.run()

    #-----------------------------------------------------------------------
    def linking(self, group=0x01, on_done=None):
        """TODO: doc
        """
        LOG.info("Device %s link mode grp %s", self.label, group)

        # This sends a linking mode command to the device.  As far as I can
        # see, there is no way to cancel it.
        msg = Msg.OutExtended.direct(self.addr, 0x09, group,
                                     bytes([0x00] * 14))
        msg_handler = handler.StandardCmd(msg, self.handle_linking, on_done)
        self.send(msg, msg_handler)

        # NOTE: this command is to enter linking mode - we get ACK back that
        # it did, but unlike the modem, we don't get a message telling us
        # what the result is when the linking actually completes.  So there
        # to be a refresh call made to the device once the linking actually
        # finishes.  So - the user must refresh the device.

    #-----------------------------------------------------------------------
    def pair(self, on_done=None):
        """Pair the device with the modem.

        This only needs to be called one time.  It will set the device
        as a controller and the modem as a responder for all of the
        groups that the device can alert on.

        The default implementation does nothing - subclasses should
        re-implement this to do proper pairing.
        """
        LOG.error("Device %s doesn't support pairing", self.label)

    #-----------------------------------------------------------------------
    def refresh(self, force=False, on_done=None):
        """Refresh the current device state and database if needed.

        This sends a ping to the device.  The reply has the current
        device state (on/off, level, etc) and the current db delta
        value which is checked against the current db value.  If the
        current db is out of date, it will trigger a download of the
        database.

        This will send out an updated signal for the current device
        status whenever possible (like dimmer levels).

        Args:
          force:    If true, will force a refresh of the device
                    database even if the delta value matches as well as
                    a requery of the device model information even if it
                    is already known.
          on_done:  Optional callback run when the commands are finished.
        """
        LOG.info("Device %s cmd: status refresh", self.label)

        # Use a sequence
        seq = CommandSeq(self.protocol, "Device refreshed", on_done)

        # This sends a refresh ping which will respond w/ the current
        # database delta field.  The handler checks that against the
        # current value.  If it's different, it will send a database
        # download command to the device to update the database.
        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x00)
        msg_handler = handler.DeviceRefresh(self, self.handle_refresh, force,
                                            None, num_retry=3)
        seq.add_msg(msg, msg_handler)

        # If model number is not known, or force true, run get_model
        if (self.db.dev_cat is None or 
            self.db.sub_cat is None or
            self.db.firmware is None or
            force):
            seq.add(self.get_model)
        
        # Alright run it all
        seq.run()

    #-----------------------------------------------------------------------
    def get_flags(self, on_done=None):
        """TODO: doc
        """
        LOG.info("Device %s cmd: get operation flags", self.label)

        # This sends a refresh ping which will respond w/ the current
        # database delta field.  The handler checks that against the
        # current value.  If it's different, it will send a database
        # download command to the device to update the database.
        msg = Msg.OutStandard.direct(self.addr, 0x1f, 0x00)
        msg_handler = handler.StandardCmd(msg, self.handle_flags, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def get_engine(self, on_done=None):
        """ Request the engine version of the device

        The engine version can be i1, i2, or i2cs.  The engine version defines
        what type of messages can be used with a device and the type of all
        link database used by a device.
        """
        LOG.info("Device %s cmd: get engine version", self.label)

        # Send the get_engine_version request.
        msg = Msg.OutStandard.direct(self.addr, 0x0D, 0x00)
        msg_handler = handler.StandardCmd(msg, self.handle_engine, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def get_model(self, on_done=None):
        """ Request the model information (dev_cat, sub_cat, and firmware)
        from the device
        """
        LOG.info("Device %s cmd: get engine version", self.label)

        # Send the get_engine_version request.
        msg = Msg.OutStandard.direct(self.addr, 0x10, 0x00)
        msg_handler = handler.BroadcastCmdResponse(msg, self.handle_model,
                                                   on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def db_add_ctrl_of(self, local_group, remote_addr, remote_group,
                       two_way=True, refresh=True, on_done=None,
                       local_data=None, remote_data=None):
        """Add the device as a controller of another device.

        This updates the devices's all link database to show that the
        device is controlling another Insteon device.  If two_way is
        True, the corresponding responder link on the other device is
        also created.  This two-way link is required for the other
        device to accept commands from this device.

        The 3 byte data entry is usually (on_level, ramp_rate, unused)
        where those values are 1 byte (0-255) values but those fields
        are device dependent.

        The optional callback has the signature:
            on_done(bool success, str message, entry)

        - success is True if both commands worked or False if any failed.
        - message is a string with a summary of what happened.  This is used
          for user interface responses to sending this command.
        - entry is either the db.ModemEntry or db.DeviceEntry that was
          updated.

        Args:
          addr:     (Address) The remote device address.
          group:    (int) The group to add link for.
          data:     (bytes[3]) 3 byte data entry.
          two_way:  (bool) If True, after creating the controller link on the
                    device, a responder link is created on the remote device
                    to form the required pair of entries.
          refresh:  (bool) If True, call refresh before changing the db.
                    Changing the db w/o an out of date db will likely require
                    a factory reset (since memory addresses are manipulated)
                    so this is important.
          on_done:  Optional callback run when both commands are finished.
        """
        is_controller = True
        self._db_update(local_group, is_controller, remote_addr, remote_group,
                        two_way, refresh, on_done, local_data, remote_data)

    #-----------------------------------------------------------------------
    def db_add_resp_of(self, local_group, remote_addr, remote_group,
                       two_way=True, refresh=True, on_done=None,
                       local_data=None, remote_data=None):
        """Add the device as a responder of another device.

        This updates the devices's all link database to show that the
        device is responding to another Insteon device.  If two_way is
        True, the corresponding controller link on the other device is
        also created.  This two-way link is required for the other
        device to accept commands from this device.

        The 3 byte data entry is usually (on_level, ramp_rate, unused)
        where those values are 1 byte (0-255) values but those fields
        are device dependent.

        The optional callback has the signature:
            on_done(bool success, str message, entry)

        - success is True if both commands worked or False if any failed.
        - message is a string with a summary of what happened.  This is used
          for user interface responses to sending this command.
        - entry is either the db.ModemEntry or db.DeviceEntry that was
          updated.

        Args:
          addr:     (Address) The remote device address.
          group:    (int) The group to add link for.
          data:     (bytes[3]) 3 byte data entry.
          two_way:  (bool) If True, after creating the responder link on the
                    device, a controller link is created on the remote device
                    to form the required pair of entries.
          refresh:  (bool) If True, call refresh before changing the db.
                    Changing the db w/o an out of date db will likely require
                    a factory reset (since memory addresses are manipulated)
                    so this is important.
          on_done:  Optional callback run when both commands are finished.

        """
        is_controller = False
        self._db_update(local_group, is_controller, remote_addr, remote_group,
                        two_way, refresh, on_done, local_data, remote_data)

    #-----------------------------------------------------------------------
    def db_del_ctrl_of(self, addr, group, two_way=True, refresh=True,
                       on_done=None):
        """TODO: doc
        """
        # Call with is_controller=True
        self._db_delete(addr, group, True, two_way, refresh, on_done)

    #-----------------------------------------------------------------------
    def db_del_resp_of(self, addr, group, two_way=True, refresh=True,
                       on_done=None):
        """TODO: doc
        """
        # Call with is_controller=False
        self._db_delete(addr, group, False, two_way, refresh, on_done)

    #-----------------------------------------------------------------------
    def link_data(self, is_controller, group, data=None):
        """TODO: doc
        """
        # Most of this is from looking through Misterhouse bug reports.
        if is_controller:
            # D1 = 0x03 number of retries to use for the command
            # D2 = ???
            # D3 = some devices need 0x01 or group number others don't care
            defaults = [0x03, 0x00, group]

        # Responder data is always link dependent.  Since nothing was given,
        # assume the user wants to turn the device on (0xff).
        else:
            # D1 = on level for on/off, dimmers
            # D2 = ramp rate for on/off, dimmers.  I believe leaving this
            #      at 0 uses the default ramp rate.
            # D3 = The local group number of the local button.  The input
            #      group is the controller group number (and broadcast msg)
            #      so this is the local button group number it maps to.
            defaults = [0xff, 0x00, group]

        # For each field, use the input if not -1, else the default.
        return util.resolve_data3(defaults, data)

    #-----------------------------------------------------------------------
    def run_command(self, **kwargs):
        """Run arbitrary commands.

        Commands are input as a dictionary:
          { 'cmd' : 'COMMAND', ...args }

        where COMMAND is the command name and any additional arguments
        to the command are other dictionary keywords.  Valid commands
        are:
          getdb:  No arguments.  Download the PLM modem all link database
                  and save it to file.

          refresh:  No arguments.  Ping the device and see if the database is
                    current.  Reloads the modem database if needed.
        """
        cmd = kwargs.pop('cmd', None)
        if not cmd:
            LOG.error("Invalid command sent to device %s.  No 'cmd' "
                      "keyword: %s", self.label, kwargs)
            return

        cmd = cmd.lower().strip()
        func = self.cmd_map.get(cmd, None)
        if not func:
            LOG.error("Invalid command sent to device %s '%s'.  Input cmd "
                      "'%s' not valid.  Valid commands: %s", self.label,
                      self.name, cmd, self.cmd_map.keys())
            return

        # Call the command function with any remaining arguments.
        try:
            func(**kwargs)
        except:
            LOG.exception("Invalid command inputs to device %s'.  Input cmd "
                          "%s with args: %s", self.label, cmd, str(kwargs))

    #-----------------------------------------------------------------------
    def handle_received(self, msg):
        """Receives incomming message notifications from protocol

        This is called for every standard and extended message that is read
        from the modem from this device.  This is only used to track the hop
        distance from the modem to each device and isn't used for general
        message handling.

        It extracts the number of hops that occurred and uses that to create
        a moving average of the distance to the device so that outbound
        messages can set the maximum hop value for the most efficient
        transfers.

        Args:
          msg:    (Msg.InpStandard, Msg.InpExtended) The message that arrived.
        """
        self.history.add(msg)

    #-----------------------------------------------------------------------
    def handle_refresh(self, msg):
        """Handle replies to the refresh command.

        The refresh command reply will contain the current device
        state in cmd2 and this updates the device with that value.

        Args:
          msg:  (message.InpStandard) The refresh message reply.  The current
                device state is in the msg.cmd2 field.
        """
        # Do nothing - derived types can override this if they have
        # state to extract and update.
        pass

    #-----------------------------------------------------------------------
    def handle_flags(self, msg, on_done):
        """TODO: doc
        """
        LOG.ui("Device %s operating flags: %s", self.addr,
               "{:08b}".format(msg.cmd2))
        on_done(True, "Operation complete", msg.cmd2)

    #-----------------------------------------------------------------------
    def handle_engine(self, msg, on_done):
        """Handle replies to the get engine command.

        The engine command reply will contain the device engine
        version in cmd2 and this updates the device with that value.

        Args:
          msg:  (message.InpStandard) The engine message reply.  The engine
                version state is in the msg.cmd2 field.
        """
        ver_num = 0x00
        if msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
            # If we get a NAK it is almost certainly because this is an I2CS
            # device that lacks a responder link.
            ver_num = 0x02
            LOG.debug("Device %s sent NAK to get engine: %s", self.addr,
                      msg.cmd2)
        else:
            ver_num = msg.cmd2

        self.db.set_engine(ver_num)

        labels = {0 : "i1", 1 : "i2", 2 : "i2c"}
        version = labels.get(msg.cmd2, "Unknown, using I2CS")
        LOG.ui("Device %s engine version: %s", self.addr, version)
        on_done(True, "Operation complete", msg.cmd2)

    #-----------------------------------------------------------------------
    def handle_model(self, msg, on_done):
        """Handle the broadcast reply to the get model command.

        The to address of the broadcast reply contains the dev_cat, sub_cat,
        and firmware

        Args:
          msg:  (message.InpStandard) The id request broadcast response.
        """
        if msg.cmd1 == 0x01:
            self.db.set_dev_cat(msg.to_addr.ids[0])
            self.db.set_sub_cat(msg.to_addr.ids[1])
            self.db.set_firmware(msg.to_addr.ids[2])
            LOG.ui("Device %s received model information, dev_cat: %#x, " +
                   "sub_cat: %#x, firmware: %#x ", self.addr, self.db.dev_cat,
                   self.db.sub_cat, self.db.firmware)
            on_done(True, "Operation complete", None)
        else:
            LOG.debug("Device %s get_model response with wrong cmd %s",
                      self.addr, msg.cmd1)

    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        """Handle broadcast messages from this device.

        The broadcast message from a device is sent when the device is
        triggered.  The message has the group ID in it.  We'll update
        the device state and look up the group in the all link
        database.  For each device that is in the group (as a
        reponsder), we'll call handle_group_cmd() on that device to
        trigger it.  This way all the devices in the group are updated
        to the correct values when we see the broadcast message.

        Args:
          msg:   (InptStandard) Broadcast message from the device.
        """
        group = msg.group

        responders = self.db.find_group(group)
        LOG.debug("Found %s responders in group %s", len(responders), group)
        LOG.debug("Group %s -> %s", group, [i.addr.hex for i in responders])

        # For each device that we're the controller of call it's
        # handler for the broadcast message.
        for elem in responders:
            device = self.modem.find(elem.addr)
            if device:
                LOG.info("%s broadcast to %s for group %s", self.label,
                         device.addr, group)
                device.handle_group_cmd(self.addr, group, msg.cmd1)
            else:
                LOG.warning("%s broadcast - device %s not found", self.label,
                            elem.addr)

    #-----------------------------------------------------------------------
    def handle_group_cmd(self, addr, group, cmd):
        """Respond to a group command for this device.

        This is called when this device is a responder to a scene.
        The device should look up the responder entry for the group in
        it's all link database and update it's state accordingly.

        Args:
          addr:  (Address) The device that sent the message.  This is the
                 controller in the scene.
          group: (int) The group being triggered.
          cmd:   (int) The command byte being sent.
        """
        # Default implementation - derived classes should specialize this.
        LOG.info("Device %s ignoring group cmd - not implemented", self.label)

    #-----------------------------------------------------------------------
    def handle_linking(self, msg, on_done=None):
        """TODO: doc
        """
        on_done = util.make_callback(on_done)

        if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
            on_done(True, "Entered linking mode", None)
        else:
            on_done(False, "Linking mode failed", None)

    #-----------------------------------------------------------------------
    def _db_update(self, local_group, is_controller, remote_addr, remote_group,
                   two_way, refresh, on_done, local_data, remote_data):
        """Update the device database.

        See db_add_ctrl_of() or db_add_resp_of() for docs.
        """
        # Find the remote device.  Update addr since the input may be a name.
        remote = self.modem.find(remote_addr)
        if remote:
            remote_addr = remote.addr

        # If don't have an entry for this device, we can't sent it commands.
        if two_way and not remote:
            LOG.ui("Device db add %s can't find remote device %s.  "
                   "Link will be only one direction",
                   util.ctrl_str(is_controller), remote_addr)

        seq = CommandSeq(self.protocol, "Device db update complete", on_done)

        # Check for a db update - otherwise we could be out of date and not
        # know it in which case the memory addresses to add the record in
        # will be wrong.
        if refresh:
            seq.add(self.refresh)

        # Get the data array to use.  See Github issue #7 for discussion.
        # Use teh bytes() cast here so we can take a list as input.
        local_data = self.link_data(is_controller, local_group, local_data)

        # Group number in the db is the group number of the controller since
        # that's the group number in the broadcast message we'll receive.
        db_group = local_group
        if not is_controller:
            db_group = remote_group

        # Create a new database entry for the device and send it.
        seq.add(self.db.add_on_device, self, remote_addr, db_group,
                is_controller, local_data)

        # For two way commands, insert a callback so that when the modem
        # command finishes, it will send the next command to the device.
        # When that finishes, it will run the input callback.
        if two_way and remote:
            two_way = False
            on_done = None
            if is_controller:
                seq.add(remote.db_add_resp_of, remote_group, self.addr,
                        local_group, two_way, refresh, local_data=remote_data)
            else:
                seq.add(remote.db_add_ctrl_of, remote_group, self.addr,
                        local_group, two_way, refresh, local_data=remote_data)

        # Start the command sequence.
        seq.run()

    #-----------------------------------------------------------------------
    def _db_delete(self, addr, group, is_controller, two_way, refresh,
                   on_done):
        """TODO: doc
        """
        # Find the remote device.  Update addr since the input may be a name.
        remote = self.modem.find(addr)
        if remote:
            addr = remote.addr

        # If don't have an entry for this device, we can't sent it commands
        if two_way and not remote:
            LOG.ui("Device db delete %s can't find remote device %s.  "
                   "Link will be only deleted one direction",
                   util.ctrl_str(is_controller), addr)

        # Find the database entry being deleted.
        entry = self.db.find(addr, group, is_controller)
        if not entry:
            LOG.warning("Device %s delete no match for %s grp %s %s",
                        self.label, addr, group, util.ctrl_str(is_controller))
            on_done(False, "Entry doesn't exist", None)
            return

        seq = CommandSeq(self.protocol, "Delete complete", on_done)

        # Check for a db update - otherwise we could be out of date and not
        # know it in which case the memory addresses to add the record in
        # will be wrong.
        if refresh:
            seq.add(self.refresh)

        seq.add(self.db.delete_on_device, self, entry)

        # For two way commands, insert a callback so that when the modem
        # command finishes, it will send the next command to the device.
        # When that finishes, it will run the input callback.
        if two_way and remote:
            if is_controller:
                seq.add(remote.db_del_resp_of, self.addr, group, two_way=False)
            else:
                seq.add(remote.db_del_ctrl_of, self.addr, group, two_way=False)

        # Start running the commands.
        seq.run()

    #-----------------------------------------------------------------------
