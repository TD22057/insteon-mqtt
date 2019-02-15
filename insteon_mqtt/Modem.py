#===========================================================================
#
# Insteon modem class.
#
#===========================================================================
import json
import os
from .Address import Address
from .CommandSeq import CommandSeq
from . import config
from . import db
from . import handler
from . import log
from . import message as Msg
from . import util
from .Signal import Signal

LOG = log.get_logger()


class Modem:
    """Insteon modem class

    The modem class handles commands to send to the PLM modem.  It also
    stores the device definitions by address (read from a configuration
    input).  This allows devices to be looked up by address to send commands
    to those devices.
    """
    def __init__(self, protocol):
        """Constructor

        Actual modem definitions must be loaded from a configuration file via
        load_config() before the modem can be used.

        Args:
          protocol (Protocol):  Insteon message handling protocol object.
        """
        self.protocol = protocol

        self.addr = None
        self.name = "modem"
        self.label = self.name

        self.save_path = None

        # Map of Address.id -> Device and name -> Device.  name is optional
        # so devices might not be in that map.
        self.devices = {}
        self.device_names = {}
        self.db = db.Modem()

        # Signal to emit when a new device is added.
        self.signal_new_device = Signal()  # emit(modem, device)

        # Remove (mqtt) commands mapped to methods calls.  These are handled
        # in run_command().  Commands should all be lower case (inputs are
        # lowered).
        self.cmd_map = {
            'db_add_ctrl_of' : self.db_add_ctrl_of,
            'db_add_resp_of' : self.db_add_resp_of,
            'db_del_ctrl_of' : self.db_del_ctrl_of,
            'db_del_resp_of' : self.db_del_resp_of,
            'get_devices' : self.get_devices,
            'print_db' : self.print_db,
            'refresh' : self.refresh,
            'refresh_all' : self.refresh_all,
            'linking' : self.linking,
            'scene' : self.scene,
            'factory_reset' : self.factory_reset,
            }

        # Add a generic read handler for any broadcast messages initiated by
        # the Insteon devices.
        self.protocol.add_handler(handler.Broadcast(self))

        # Handle all link complete messages that the modem sends when the set
        # button or linking mode is finished.
        self.protocol.add_handler(handler.ModemLinkComplete(self))

        # Handle user triggered factory reset of the modem.
        self.protocol.add_handler(handler.ModemReset(self))

        # Log messages as they received so we can track the message hop count
        # to each device.
        self.protocol.signal_received.connect(self.handle_received)

    #-----------------------------------------------------------------------
    def type(self):
        """Return a nice class name for the device.
        """
        return "Modem"

    #-----------------------------------------------------------------------
    def load_config(self, data):
        """Load a configuration dictionary.

        This should be the insteon key in the configuration data.  Key inputs
        are:

        - port      The serial device to talk to.  This is a path to the
                    modem (or a network url).  See pyserial for inputs.
        - baudrate  Optional baud rate of the serial line.
        - address   Insteon address of the modem.  See Address for inputs.
        - storage   Path to store database records in.
        - startup_refresh    True if device databases should be checked for
                             new entries on start up.
        - devices   List of devices.  Each device is a type and insteon
                    address of the device.

        Args:
          data (dict):  Configuration data to load.
        """
        LOG.info("Loading configuration data")

        # Pass the data to the modem network link.
        self.protocol.load_config(data)

        # Read the modem address.
        self.addr = Address(data['address'])
        self.label = "%s (%s)" % (self.addr, self.name)
        LOG.info("Modem address set to %s", self.addr)

        # Load the modem database.
        if 'storage' in data:
            save_path = data['storage']
            if not os.path.exists(save_path):
                os.makedirs(save_path)

            self.save_path = save_path
            self.load_db()

            LOG.info("Modem %s database loaded %s entries", self.addr,
                     len(self.db))
            LOG.debug(str(self.db))

        # Read the device definitions and scenes.
        self._load_devices(data.get('devices', []))
        #FUTURE: self.scenes = self._load_scenes(data.get('scenes', []))

        # Send refresh messages to each device to check if the database is up
        # to date.
        if data.get('startup_refresh', False) is True:
            LOG.info("Starting device refresh")
            for device in self.devices.values():
                device.refresh()

    #-----------------------------------------------------------------------
    def refresh(self, force=False, on_done=None):
        """Load the all link database from the modem.

        This sends a message to the modem to start downloading the all link
        database.  The message handler handler.ModemDbGet is used to process
        the replies and update the modem database.

        Args:
          force (bool):  Ignored - this insures a consistent API with the
                device refresh command.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Modem sending get first db record command")

        # Clear the db so we can rebuild it.
        self.db.clear()

        # Request the first db record from the handler.  The handler will
        # request each next record as the records arrive.
        msg = Msg.OutAllLinkGetFirst()
        msg_handler = handler.ModemDbGet(self.db, on_done)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def db_path(self):
        """Return the all link database path.

        This will be the configuration save_path directory and the file name
        will be the modem hex address with a .json suffix.
        """
        return os.path.join(self.save_path, self.addr.hex) + ".json"

    #-----------------------------------------------------------------------
    def load_db(self):
        """Load the all link database from a file.

        The file is stored in JSON format (by save_db()) and has the path
        self.db_path().  If the file doesn't exist, nothing is done.
        """
        # See if the database file exists.  Tell the modem it's future path
        # so it can save itself.
        path = self.db_path()
        self.db.set_path(path)
        if not os.path.exists(path):
            return

        # Read the file and convert it to a db.Modem object.
        try:
            with open(path) as f:
                data = json.load(f)

            self.db = db.Modem.from_json(data, path)
        except:
            LOG.exception("Error reading modem db file %s", path)
            return

        LOG.info("%s database loaded %s entries", self.addr, len(self.db))
        LOG.debug("%s", self.db)

    #-----------------------------------------------------------------------
    def print_db(self, on_done):
        """Print the device database to the log UI.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.ui("%s modem database", self.addr)
        LOG.ui("%s", self.db)
        on_done(True, "Complete", None)

    #-----------------------------------------------------------------------
    def add(self, device):
        """Add a device object to the modem.

        This doesn't change the modem all link database, it just allows us to
        find the input device by address.

        Args:
          device:  The device object to add.
        """
        self.devices[device.addr.id] = device
        if device.name:
            self.device_names[device.name] = device

    #-----------------------------------------------------------------------
    def remove(self, device):
        """Remove a device object from the modem.

        This doesn't change the modem all link database, it just removes the
        input device from our local look up.

        Args:
          device: The device object to add.  If the device doesn't exist,
                  nothing is done.
        """
        self.devices.pop(device.addr.id, None)
        if device.name:
            self.device_names.pop(device.name, None)

    #-----------------------------------------------------------------------
    def find(self, addr):
        """Find a device by address.

        NOTE: this searche devices in the config file.  We don't ping the
        modem to find the devices because disovery isn't the most reliable.

        Args:
          addr (Address): The Insteon address object to find.  This can
               also be a string or integer (see the Address constructor for
               other options.  This can also be the modem address in which
               case this object is returned.

        Returns:
          Returns the device object or None if it doesn't exist.
        """
        # Handle string device name requests.
        if isinstance(addr, str):
            addr = addr.lower()

        if addr == "modem":
            return self

        # See if the input is one of the "nice" device names.
        device = self.device_names.get(addr, None)
        if device:
            return device

        # Otherwise, try and parse the input as an Insteon address.
        try:
            addr = Address(addr)
        except:
            LOG.exception("Invalid Insteon address or unknown device name "
                          "'%s'", addr)
            return None

        # Device address is the modem.
        if addr == self.addr:
            return self

        # Otherwise try and find the device by address.  None is
        # returned if it doesn't exist.
        device = self.devices.get(addr.id, None)
        return device

    #-----------------------------------------------------------------------
    def refresh_all(self, force=False, on_done=None):
        """Refresh all the all link databases.

        This forces a refresh of the modem and device databases.  This can
        take a long time - up to 5 seconds per device some times depending on
        the database sizes.  So it usually should only be called if no other
        activity is expected on the network.

        Args:
          force (bool):  Force flag passed to devices.  If True, devices
                will refresh their Insteon db's even if they think the db
                is up to date.
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
        """
        # Set the error stop to false so a failed refresh doesn't stop the
        # sequence from trying to refresh other devices.
        seq = CommandSeq(self.protocol, "Refresh all complete", on_done,
                         error_stop=False)

        # Reload the modem database.
        seq.add(self.refresh, force)

        # Reload all the device databases.
        for device in self.devices.values():
            seq.add(device.refresh, force)

        # Start the command sequence.
        seq.run()

    #-----------------------------------------------------------------------
    def get_devices(self, on_done=None):
        """"Print all the devices the modem knows about to the log UI.

        Args:
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
        """
        LOG.ui(json.dumps(self.info_entry()))

        seen = set()
        for e in self.db.entries:
            if e.addr in seen:
                continue

            device = self.devices.get(e.addr.id, None)
            if device:
                entry = device.info_entry()
            else:
                entry = {str(e.addr) : {"type" : "unknown"}}

            LOG.ui(json.dumps(entry))
            seen.add(e.addr)

        on_done(True, "Complete", None)

    #-----------------------------------------------------------------------
    def info_entry(self):
        """Return a JSON dictionary containing information about the device.
        """
        return {str(self.addr) : {
            "type" : "modem",
            "label" : self.name,
            }}

    #-----------------------------------------------------------------------
    def db_add_ctrl_of(self, local_group, remote_addr, remote_group,
                       two_way=True, refresh=True, on_done=None,
                       local_data=None, remote_data=None):
        """Add the modem as a controller of a device.

        This updates the modem's all link database to show that the model is
        controlling an Insteon device.  If two_way is True, the corresponding
        responder link on the device is also created.  This two-way link is
        required for the device to accept commands from the modem.

        Normally, pressing the set button the modem and then the device will
        configure this link using group 1.

        The 3 byte data entry is usually (on_level, ramp_rate, unused) where
        those values are 1 byte (0-255) values but those fields are device
        dependent.

        The optional callback has the signature:
            on_done(bool success, str message, entry)

        - success is True if both commands worked or False if any failed.
        - message is a string with a summary of what happened.  This is used
          for user interface responses to sending this command.
        - entry is either the db.ModemEntry or db.DeviceEntry that was
          updated.

        Args:
          local_group (int):  The modem group to use as the scene number.
          remote_addr (Address):  The address of the device to control.
          remote_group (int):  The group on the remote address to control.
          two_way (bool):  If True, after creating the controller link on the
                  modem, a responder link is created on the remote device
                  to form the required pair of entries.
          refresh (bool):  If True, call refresh before changing the db.
                  This is ignored on the modem since it doesn't use memory
                  addresses and can't be corrupted.
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
          local_data (bytes[3]):  The local 3 byte data array to set on the
                     modem db entry.  If this is None, it will be assigned
                     automatically.
          remote_data (bytes[3]):  The remote 3 byte data array to set on the
                      remote device.  If this is None, it will be assigned
                      automatically.
        """
        is_controller = True
        self._db_update(local_group, is_controller, remote_addr, remote_group,
                        two_way, refresh, on_done, local_data, remote_data)

    #-----------------------------------------------------------------------
    def db_add_resp_of(self, local_group, remote_addr, remote_group,
                       two_way=True, refresh=True, on_done=None,
                       local_data=None, remote_data=None):
        """Add the modem as a responder of a device.

        This updates the modem's all link database to show that the model is
        responding to an Insteon device.  If two_way is True, the
        corresponding controller link on the device is also created.  This
        two-way link is required for the device to send commands to the modem
        and for the modem to report device state changes.

        Normally, pressing the set button the device and then the modem will
        configure this link using group 1.

        The 3 byte data entry is usually (on_level, ramp_rate, unused) where
        those values are 1 byte (0-255) values but those fields are device
        dependent.

        The optional callback has the signature:
            on_done(bool success, str message, entry)

        - success is True if both commands worked or False if any failed.
        - message is a string with a summary of what happened.  This is used
          for user interface responses to sending this command.
        - entry is either the db.ModemEntry or db.DeviceEntry that was
          updated.

        Args:
          local_group (int):  The modem group to use as the scene number.
          remote_addr (Address):  The address of the device to respond to.
          remote_group (int):  The group on the remote address to respond to.
          two_way (bool):  If True, after creating the responder link on the
                  modem, a controller link is created on the remote device
                  to form the required pair of entries.
          refresh (bool):  If True, call refresh before changing the db.
                  This is ignored on the modem since it doesn't use memory
                  addresses and can't be corrupted.
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
          local_data (bytes[3]):  The local 3 byte data array to set on the
                     modem db entry.  If this is None, it will be assigned
                     automatically.
          remote_data (bytes[3]):  The remote 3 byte data array to set on the
                      remote device.  If this is None, it will be assigned
                      automatically.
        """
        is_controller = False
        self._db_update(local_group, is_controller, remote_addr, remote_group,
                        two_way, refresh, on_done, local_data, remote_data)

    #-----------------------------------------------------------------------
    def db_del_ctrl_of(self, addr, group, two_way=True, refresh=True,
                       on_done=None):
        """Delete the modem as a controller of a device.

        This updates the modem's all link database to remove a record where
        the modem is controlling another device.  If two_way is True, the
        corresponding responder link on the device is also remove.

        The optional callback has the signature:
            on_done(bool success, str message, entry)

        - success is True if both commands worked or False if any failed.
        - message is a string with a summary of what happened.  This is used
          for user interface responses to sending this command.
        - entry is either the db.ModemEntry or db.DeviceEntry that was
          removed.

        If the requested record doesn't exist, it's considered an error and
        on_done is called with success=False.

        Args:
          addr (Address):  The remote device address to delete on the modem.
          group (int):  The group on the modem to delete the link for.
          two_way (bool):  If True, after deleting the controller link on the
                  modem, the responder link is deleted on the remote device
                  to clean up the pair of entries.
          refresh (bool):  If True, call refresh before changing the db.
                  This is ignored on the modem since it doesn't use memory
                  addresses and can't be corrupted.
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
        """
        # Call with is_controller=True
        self._db_delete(addr, group, True, two_way, refresh, on_done)

    #-----------------------------------------------------------------------
    def db_del_resp_of(self, addr, group, two_way=True, refresh=True,
                       on_done=None):
        """Delete the modem as a responder of a device.

        This updates the modem's all link database to remove a record where
        the modem is responding to another device.  If two_way is True, the
        corresponding controller link on the device is also remove.

        The optional callback has the signature:
            on_done(bool success, str message, entry)

        - success is True if both commands worked or False if any failed.
        - message is a string with a summary of what happened.  This is used
          for user interface responses to sending this command.
        - entry is either the db.ModemEntry or db.DeviceEntry that was
          removed.

        If the requested record doesn't exist, it's considered an error and
        on_done is called with success=False.

        Args:
          addr (Address):  The remote device address to delete on the modem.
          group (int):  The group on the modem to delete the link for.
          two_way (bool):  If True, after deleting the responder link on the
                  modem, the controller link is deleted on the remote device
                  to clean up the pair of entries.
          refresh (bool):  If True, call refresh before changing the db.
                  This is ignored on the modem since it doesn't use memory
                  addresses and can't be corrupted.
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
        """
        # Call with is_controller=False
        self._db_delete(addr, group, False, two_way, refresh, on_done)

    #-----------------------------------------------------------------------
    def factory_reset(self, on_done=None):
        """Factory reset the modem.

        This will erase all the entries on the modem.

        Args:
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
        """
        LOG.warning("Modem being reset.  All data will be lost")
        msg = Msg.OutResetModem()
        msg_handler = handler.ModemReset(self, on_done)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def linking(self, group=0x01, on_done=None):
        """Enable linking mode on the modem.

        This is the same as pressing the set button on the modem.

        Args:
          group (int):  The group number to to set in the modem when the link
                is created.
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
        """
        # Tell the modem to enter all link mode for the group.  The
        # handler will handle timeouts (to send the cancel message) if
        # nothing happens.  See the handler for details.
        msg = Msg.OutModemLinking(Msg.OutModemLinking.Cmd.EITHER, group)
        msg_handler = handler.ModemLinkStart(on_done)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def link_data(self, is_controller, group, data=None):
        """Create a 3 byte link data array for the modem.

        If data is not input, the default data for a controller record will
        be [group, 0x00, 0x00].  The default data for a responder record will
        be [group, 0x00, 0x00].

        Args:
           is_controller (bool):  True if the link will be for the modem
                         as a controller.
           group (int): The group on the modem the link is for.
           data ([D1,D2,D3]):   The data bytes to set on the modem.

        Returns:
           bytes[3]:  Returns a list of 3 bytes to use as the data record.
        """
        # Normally, the modem (ctrl) -> device (resp) link is created using
        # the linking() command - then the handler.ModemLinkComplete will
        # fill these values in for us using the device information.  But they
        # probably aren't used so it doesn't really matter.
        if is_controller:
            defaults = [group, 0x00, 0x00]

        # Responder data is a mystery on the modem.  This seems to work but
        # it's unclear if it's needed at all.
        else:
            defaults = [group, 0x00, 0x00]

        # For each field, use the input if not -1, else the default.
        return util.resolve_data3(defaults, data)

    #-----------------------------------------------------------------------
    def scene(self, is_on, group, num_retry=3, on_done=None):
        """Trigger a virtual modem scene.

        This will send out a scene command from the modem.  When the scene
        message is ACK'ed, Modem.handle_scene will be called.

        Args:
          is_on (bool): True to send an on (0x11) command for the scene.
                False to send an off (0x13) command for the scene.
          group (int):  The modem group (scene) number to send.
          num_retry (int):  The number of retries to use if the message fails.
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
        """
        assert 0x01 <= group <= 0xff
        LOG.info("Modem scene %s on=%s", group, "on" if is_on else "off")

        cmd1 = 0x11 if is_on else 0x13
        msg = Msg.OutModemScene(group, cmd1, 0x00)
        msg_handler = handler.ModemScene(self, msg, on_done)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def handle_received(self, msg):
        """Receives incomming message notifications from protocol

        This is called for every message that is read from the modem.  For
        standard and extended messages, it will find the device the message
        is from and notify them it was received.  This is only used to track
        the hop distance from the modem to each device and isn't used for
        general message handling.

        Args:
          msg (Msg.Base):  The message that arrived.
        """
        if not isinstance(msg, (Msg.InpStandard, Msg.InpExtended)):
            return

        device = self.find(msg.from_addr)
        if device:
            device.handle_received(msg)

    #-----------------------------------------------------------------------
    def handle_scene(self, msg):
        """Callback for scene simulation commanded messages.

        This callback is run when we get a reply back from triggering a scene
        on the device.  If the command was ACK'ed, we know it worked.  The
        device will then update the states on the devices in the scene.

        Args:
          msg (InpStandard):  Broadcast message from the device.  Use
              msg.group to find the group and msg.cmd1 for the command.
        """
        group = msg.group

        responders = self.db.find_group(group)
        LOG.debug("Found %s responders in group %s", len(responders), group)
        LOG.debug("Group %s -> %s", group, [i.addr.hex for i in responders])

        # For each device that we're the controller of call it's
        # handler for the broadcast message.
        for elem in responders:
            device = self.find(elem.addr)
            if device:
                LOG.info("%s broadcast to %s for group %s", self.label,
                         device.addr, group)
                device.handle_group_cmd(self.addr, msg)
            else:
                LOG.warning("%s broadcast - device %s not found", self.label,
                            elem.addr)

    #-----------------------------------------------------------------------
    def run_command(self, **kwargs):
        """Run arbitrary commands.

        Commands are input as a dictionary:
          { 'cmd' : 'COMMAND', ...args }

        where COMMAND is the command name and any additional arguments to the
        command are other dictionary keywords.  Valid commands are:

          getdb:  No arguments.  Download the PLM modem all link database
                  and save it to file.

          reload_all: No arguments.  Reloads the modem database and tells
                      every device to reload it's database as well.

          factory_reset: No arguments.  Full factory reset of the modem.

          set_btn: Optional time_out argument (in seconds).  Simulates pressing
                   the modem set button to put the modem in linking mode.

        Args:
          kwargs:  Command dictionary containing the arguments.
        """
        cmd = kwargs.pop('cmd', None)
        if not cmd:
            LOG.error("Invalid command sent to modem %s.  No 'cmd' "
                      "keyword: %s", self.addr, kwargs)
            return

        cmd = cmd.lower().strip()
        func = self.cmd_map.get(cmd, None)
        if not func:
            LOG.error("Invalid command sent to modem %s.  Input cmd "
                      "'%s' not valid.  Valid commands: %s", self.addr,
                      cmd, self.cmd_map.keys())
            return

        # Call the command function with any remaining arguments.
        try:
            func(**kwargs)
        except:
            LOG.exception("Invalid command inputs to modem %s.  Input "
                          "cmd %s with args: %s", self.addr, cmd, str(kwargs))

    #-----------------------------------------------------------------------
    def handle_group_cmd(self, addr, msg):
        """Handle a group command addressed to the modem.

        This is called when a broadcast message is sent from a device that is
        triggered (like a motion sensor or clicking a light switch).  The
        device that sent the message will look up it's associations in it's
        all link database and call the handle_group_cmd() on each device that
        are in it's scene.

        Args:
           addr (Address):  The address the message is from.
           msg (message.InpStandard):   Broadcast group message.
        """
        # The modem has nothing to do for these messages.
        pass

    #-----------------------------------------------------------------------
    def _load_devices(self, data):
        """Load device definitions from a configuration data object.

        The input is the insteon.devices configuration dictionary.  Keys are
        the device type.  Value is the list of devices.  See config.yaml or
        the package documentation for an example.

        Args:
          data:   Configuration devices dictionary.
        """
        # Add ourselves as a device.
        self.signal_new_device.emit(self, self)

        self.devices.clear()
        self.device_names.clear()

        for device_type in data:
            # Use a default list so that if the config field is empty, the
            # loop below will still work.
            values = data[device_type]
            if not values:
                values = []

            # Look up the device type in the configuration data and call the
            # constructor to build the device object.
            dev_class, kwargs = config.find(device_type)

            # Have the device type parse the config values below here and
            # return us a list of devices.
            devices = dev_class.from_config(values, self.protocol, self,
                                            **kwargs)

            for dev in devices:
                LOG.info("Created %s at %s", device_type, dev.label)

                # Store the device by ID in the map.
                self.add(dev)

                # Notify anyone else that new device is available.
                self.signal_new_device.emit(self, dev)

    #-----------------------------------------------------------------------
    def _load_scenes(self, data):
        """Load virtual modem scenes from a configuration dict.

        Load scenes from the configuration file.  Virtual scenes are defined
        in software - they are links where the modem is the controller and
        devices are the responders.  These are scenes we can trigger by a
        command to the modem which will broadcast a message to update all the
        edeives.

        Args:
          data:   Configuration dictionary for scenes.
        """
        # FUTURE: support scene loading
        # Read scenes from the configuration file.  See if the scene has
        # changed vs what we have in the device databases.  If it has, we
        # need to update the device databases.
        scenes = {}
        return scenes

    #-----------------------------------------------------------------------
    def _db_update(self, local_group, is_controller, remote_addr, remote_group,
                   two_way, refresh, on_done, local_data, remote_data):
        """Update the modem database.

        See db_add_ctrl_of() or db_add_resp_of() for docs.
        """
        # Find the remote device.  Update addr since the input may be a name.
        remote = self.find(remote_addr)
        if remote:
            remote_addr = remote.addr

        # If don't have an entry for this device, we can't sent it commands.
        if two_way and not remote:
            LOG.info("Modem db add %s can't find remote device %s.  "
                     "Link will be only one direction",
                     util.ctrl_str(is_controller), remote_addr)

        # Get the modem data array to use.  See Github issue #7 for
        # discussion.
        local_data = self.link_data(is_controller, local_group, local_data)

        seq = CommandSeq(self.protocol, "Device db update complete", on_done)

        # Create a new database entry for the modem and send it to the modem
        # for updating.
        entry = db.ModemEntry(remote_addr, local_group, is_controller,
                              local_data)
        seq.add(self.db.add_on_device, self.protocol, entry)

        # For two way commands, insert a callback so that when the modem
        # command finishes, it will send the next command to the device.
        # When that finishes, it will run the input callback.
        if two_way and remote:
            two_way = False
            on_done = None
            if is_controller:
                seq.add(remote.db_add_resp_of, remote_group, self.addr,
                        local_group, two_way, refresh, remote_data=remote_data)
            else:
                seq.add(remote.db_add_ctrl_of, remote_group, self.addr,
                        local_group, two_way, refresh, remote_data=remote_data)

        # Start the command sequence.
        seq.run()

    #-----------------------------------------------------------------------
    def _db_delete(self, addr, group, is_controller, two_way, refresh,
                   on_done):
        """Delete a link entry on the modem.

        This updates the modem's all link database to remove a record.  If
        two_way is True, the corresponding link on the remote device is also
        remove.

        See db_del_ctrl_of() or db_del_resp_of() for docs.
        """
        LOG.debug("db delete: %s grp=%s ctrl=%s 2w=%s", addr, group,
                  util.ctrl_str(is_controller), two_way)

        # Find the remote device.  Update addr since the input may be a name.
        remote = self.find(addr)
        if remote:
            addr = remote.addr

        # If don't have an entry for this device, we can't sent it commands
        if two_way and not remote:
            LOG.ui("Device db delete %s can't find remote device %s.  "
                   "Link will be only deleted one direction",
                   util.ctrl_str(is_controller), addr)

        # Find teh database entry being deleted.
        entry = self.db.find(addr, group, is_controller)
        if not entry:
            LOG.warning("Device %s delete no match for %s grp %s %s",
                        self.addr, addr, group, util.ctrl_str(is_controller))
            on_done(False, "Entry doesn't exist", None)
            return

        # Add the function delete call to the sequence.
        seq = CommandSeq(self.protocol, "Delete complete", on_done)
        seq.add(self.db.delete_on_device, self.protocol, entry)

        # For two way commands, insert a callback so that when the modem
        # command finishes, it will send the next command to the device.
        # When that finishes, it will run the input callback.
        if two_way and remote:
            two_way = False
            if is_controller:
                seq.add(remote.db_del_resp_of, self.addr, group, two_way,
                        refresh)
            else:
                seq.add(remote.db_del_ctrl_of, self.addr, group, two_way,
                        refresh)

        # Start running the commands.
        seq.run()

    #-----------------------------------------------------------------------
