#===========================================================================
#
# Insteon modem class.
#
#===========================================================================
import functools
import json
import os
from .Address import Address
from . import config
from . import db
from . import handler
from . import log
from . import message as Msg
from .Signal import Signal

LOG = log.get_logger()


class Modem:
    """Insteon modem class

    The modem class handles commands to send to the PLM modem.  It
    also stores the device definitions by address (read from a
    configuration input).  This allows devices to be looked up by
    address to send commands to those devices.
    """
    def __init__(self, protocol):
        """Constructor

        Actual modem definitions must be loaded from a configuration
        file via load_config() before the modem can be used.

        Args:
          protocol:  (Protocol) Insteon message handling protocol object.
        """
        self.protocol = protocol
        self.addr = None
        self.save_path = None

        # Map of Address.id -> Device and name -> Device.  name is
        # optional so devices might not be in that map.
        self.devices = {}
        self.device_names = {}
        self.scenes = {}
        self.db = db.Modem()

        # Signal to emit when a new device is added.
        self.signal_new_device = Signal()  # emit(modem, device)

        # Remove (mqtt) commands mapped to methods calls.  These are
        # handled in run_command().  Commands should all be lower case
        # (inputs are lowered).
        self.cmd_map = {
            'db_add_ctrl_of' : self.db_add_ctrl_of,
            'db_add_resp_of' : self.db_add_resp_of,
            'db_delete' : self.db_delete,
            'db_get' : self.db_get,
            'refresh' : self.db_get,
            'reload_all' : self.reload_all,
            'set_btn' : self.set_btn,
            }

        # Add a generic read handler for any broadcast messages
        # initiated by the Insteon devices.
        self.protocol.add_handler(handler.Broadcast(self))

        # Handle user triggered factory reset of the modem.
        self.protocol.add_handler(handler.ModemReset(self))

    #-----------------------------------------------------------------------
    def load_config(self, data):
        """Load a configuration dictionary.

        This should be the insteon key in the configuration data.  Key
        inputs are:

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
          data:   (dict) Configuration data to load.
        """
        LOG.info("Loading configuration data")

        # Pass the data to the modem network link.
        self.protocol.load_config(data)

        # Read the modem address.
        self.addr = Address(data['address'])
        LOG.info("Modem address set to %s", self.addr)

        # Load the modem database.
        if 'storage' in data:
            self.save_path = data['storage']
            self.load_db()

            LOG.info("Modem %s database loaded %s entries", self.addr,
                     len(self.db))
            LOG.debug(str(self.db))

        # Read the device definitions and scenes.
        self._load_devices(data.get('devices', []))
        #FUTURE: self.scenes = self._load_scenes(data.get('scenes', []))

        # Send refresh messages to each device to check if the
        # database is up to date.
        if data.get('startup_refresh', False) is True:
            LOG.info("Starting device refresh")
            for device in self.devices.values():
                device.refresh()

    #-----------------------------------------------------------------------
    def db_get(self):
        """Load the all link database from the modem.

        This sends a message to the modem to start downloading the all
        link database.  The message handler handler.ModemDbGet is used to
        process the replies and update the modem database.
        """
        LOG.info("Modem sending get first db record command")

        # Clear the db so we can rebuild it.
        self.db.clear()

        # Request the first db record from the handler.  The handler
        # will request each next record as the records arrive.
        msg = Msg.OutAllLinkGetFirst()
        msg_handler = handler.ModemDbGet(self.db)
        self.protocol.send(msg, msg_handler)

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
        # See if the database file exists.  Tell the modem it's future
        # path so it can save itself.
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
    def add(self, device):
        """Add a device object to the modem.

        This doesn't change the modem all link database, it just
        allows us to find the input device by address.

        Args:
          device    The device object to add.

        """
        self.devices[device.addr.id] = device
        if device.name:
            self.device_names[device.name] = device

    #-----------------------------------------------------------------------
    def remove(self, device):
        """Remove a device object from the modem.

        This doesn't change the modem all link database, it just
        removes the input device from our local look up.

        Args:
          device    The device object to add.  If the device doesn't exist,
                    nothing is done.
        """
        self.devices.pop(device.addr.id, None)
        if device.name:
            self.device_names.pop(device.name, None)

    #-----------------------------------------------------------------------
    def find(self, addr):
        """Find a device by address.

        NOTE: this searches devices in the config file.  We don't ping
        the modem to find the devices because disovery isn't the most
        reliable.

        Args:
          addr:   (Address) The Insteon address object to find.  This can
                  also be a string or integer (see the Address constructor for
                  other options.  This can also be the modem address in which
                  case this object is returned.

        Returns:
          Returns the device object or None if it doesn't exist.
        """
        # See if the input is a nice name first.
        device = self.device_names.get(addr, None)
        if device:
            return device

        # Insure we have an Address object.
        addr = Address(addr)
        if addr == self.addr:
            return self

        device = self.devices.get(addr.id, None)
        if device:
            return device

        return None

    #-----------------------------------------------------------------------
    def reload_all(self):
        """Reload all the all link databases.

        This forces a refresh of the modem and device databases.  This
        can take a long time - up to 5 seconds per device some times
        depending on the database sizes.  So it usually should only be
        called if no other activity is expected on the network.
        """
        # Reload the modem database.
        self.db_get()

        # Reload all the device databases.
        for device in self.devices.values():
            device.db_get()

    #-----------------------------------------------------------------------
    def db_add_ctrl_of(self, addr, group, data=None, two_way=True,
                       on_done=None):
        """Add the modem as a controller of a device.

        This updates the modem's all link database to show that the
        model is controlling an Insteon device.  If two_way is True,
        the corresponding responder link on the device is also
        created.  This two-way link is required for the device to
        accept commands from the modem.

        Normally, pressing the set button the modem and then the
        device will configure this link using group 1.

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
                    modem, a responder link is created on the remote device
                    to form the required pair of entries.
          on_done:  Optional callback run when both commands are finished.
        """
        self._db_update(addr, group, data, two_way, is_controller=True,
                        on_done=on_done)

    #-----------------------------------------------------------------------
    def db_add_resp_of(self, addr, group, data=None, two_way=True,
                       on_done=None):
        """Add the modem as a responder of a device.

        This updates the modem's all link database to show that the
        model is responding to an Insteon device.  If two_way is True,
        the corresponding controller link on the device is also
        created.  This two-way link is required for the device to send
        commands to the modem and for the modem to report device state
        changes.

        Normally, pressing the set button the device and then the
        modem will configure this link using group 1.

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
                    modem, a controller link is created on the remote device
                    to form the required pair of entries.
          on_done:  Optional callback run when both commands are finished.
        """
        self._db_update(addr, group, data, two_way, is_controller=False,
                        on_done=on_done)

    #-----------------------------------------------------------------------
    def db_delete(self, addr, group, two_way=True, on_done=None):
        """TODO: doc
        """
        # Find all the entries that are going to be deleted.
        entries = self.db.find_all(addr, group)
        if not entries:
            LOG.error("No entries matching %s grp %s", addr, group)
            if on_done:
                on_done(False, "Invalid entry to delete from modem")
            return

        # Find the remote device.  If don't have an entry for this
        # device, we can't sent it commands
        remote = self.find(addr)
        if two_way and not remote:
            LOG.info("Modem db delete can't find remote device %s.  "
                     "Delete will be only one direction", addr)

        # For two way commands, insert a callback so that when the
        # modem command finishes, it will send the next command to the
        # device.  When that finishes, it will run the input callback.
        use_cb = on_done
        if two_way and remote:
            use_cb = functools.partial(self._db_update_remote, remote, on_done,
                                       False)

        # Run the delete command once for each entry.
        # TODO: how to mark command as done? - need to know how many
        # calls are gong to be attempted.
        for entry in entries:  # pylint: disable=unused-variable
            self.db.delete_on_device(self.protocol, addr, group, use_cb)

    #-----------------------------------------------------------------------
    def factory_reset(self):
        """TODO: doc
        """
        LOG.warning("Modem being reset.  All data will be lost")
        msg = Msg.OutResetPlm()
        msg_handler = handler.ModemReset(self)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def set_btn(self, group=0x01, time_out=60):
        """TODO: doc
        """
        # Tell the modem to enter all link mode for the group.  The
        # handler will handle timeouts (to send the cancel message) if
        # nothing happens.  See the handler for details.
        msg = Msg.OutAllLinkStart(Msg.OutAllLinkStart.Cmd.EITHER, group)
        msg_handler = handler.ModemAllLink(self.db, time_out)
        self.protocol.send(msg, msg_handler)

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

          reload_all: No arguments.  Reloads the modem database and tells
                      every device to reload it's database as well.

          factory_reset: No arguments.  Full factory reset of the modem.

          set_btn: Optional time_out argument (in seconds).  Simulates pressing
                   the modem set button to put the modem in linking mode.
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

        # TODO: need session arg - if set, pass callback to func which
        # it will call when finished.  Callback should publish a reply
        # to message w/ results.  This callback should be an input to
        # this function - set it in the MQTT client.

        # Call the command function with any remaining arguments.
        try:
            func(**kwargs)
        except:
            LOG.exception("Invalid command inputs to modem %s.  Input "
                          "cmd %s with args: %s", self.addr, cmd, str(kwargs))

    #-----------------------------------------------------------------------
    def handle_group_cmd(self, addr, msg):
        """Handle a group command addressed to the modem.

        This is called when a broadcast message is sent from a device
        that is triggered (like a motion sensor or clicking a light
        switch).  The device that sent the message will look up it's
        associations in it's all link database and call the
        handle_group_cmd() on each device that are in it's scene.

        Args:
           addr:   (Address) The address the message is from.
           msg:    (message.InpStandard) Broadcast group message.
        """
        # The modem has nothing to do for these messages.
        pass

    #-----------------------------------------------------------------------
    def _load_devices(self, data):
        """Load device definitions from a configuration data object.

        The input is the insteon.devices configuration dictionary.
        Keys are the device type.  Value is the list of devices.  See
        config.yaml or the package documentation for an example.

        Args:
          data:   Configuration devices dictionary.
        """
        self.devices.clear()
        self.device_names.clear()

        for device_type in data:
            # Use a default list so that if the config field is empty,
            # the loop below will still work.
            values = data[device_type]
            if not values:
                values = []

            # Look up the device type in the configuration data and
            # call the constructor to build the device object.
            ctor = config.find(device_type)

            # Call the ctor for each device that was input.
            for device_config in values:
                # If it's a dict, it's got a nice name set.
                if isinstance(device_config, dict):
                    assert len(device_config) == 1
                    addr, name = next(iter(device_config.items()))

                # Otherwise it's just the address
                else:
                    addr = device_config
                    name = None

                # Create the device
                device = ctor(self.protocol, self, addr, name)
                LOG.info("Created %s at %s '%s'", device_type, addr, name)

                # Load any existing all link database for this device if
                # it exists.
                if self.save_path:
                    device.save_path = self.save_path
                    device.load_db()

                # Store the device by ID in the map.
                self.add(device)

                # Notify anyone else that new device is available.
                self.signal_new_device.emit(self, device)

    #-----------------------------------------------------------------------
    def _load_scenes(self, data):
        """Load virtual modem scenes from a configuration dict.

        Load scenes from the configuration file.  Virtual scenes are
        defined in software - they are links where the modem is the
        controller and devices are the responders.  These are scenes
        we can trigger by a command to the modem which will broadcast
        a message to update all the edeives.

        Args:
          data:   Configuration dictionary for scenes.
        """
        # TODO: support scene loading
        # Read scenes from the configuration file.  See if the scene
        # has changed vs what we have in the device databases.  If it
        # has, we need to update the device databases.
        scenes = {}
        return scenes

    #-----------------------------------------------------------------------
    def _db_update(self, addr, group, data, two_way, is_controller, on_done):
        """Update the modem database.

        See db_add_ctrl_of() or db_add_resp_of() for docs.
        """
        # Find the remote device.  If don't have an entry for this
        # device, we can't sent it commands
        remote = self.find(addr)
        if two_way and not remote:
            lbl = "CTRL" if is_controller else "RESP"
            LOG.info("Modem db add %s can't find remote device %s.  "
                     "Link will be only one direction", lbl, addr)

        # For two way commands, insert a callback so that when the
        # modem command finishes, it will send the next command to the
        # device.  When that finishes, it will run the input callback.
        use_cb = on_done
        if two_way and remote:
            use_cb = functools.partial(self._db_update_remote, remote, on_done,
                                       True)

        # Create a new database entry for the modem and send it to the
        # modem for updating.
        entry = db.ModemEntry(addr, group, is_controller, data)
        self.db.add_on_device(self.protocol, entry, use_cb)

    #-----------------------------------------------------------------------
    def _db_update_remote(self, remote, on_done, is_add, success, msg, entry):
        """Modem device update complete callback.

        This is called when the modem finishes updating the database.
        It triggers a corresponding call on the remote device to
        establish the two way link.  This only occurs if the first
        command works.
        """
        # Update failed - call the user callback and return
        if not success:
            if on_done:
                on_done(False, msg, entry)
            return

        # Send the command to the device.  Two way is false here since
        # we just added the other link.
        two_way = False
        if is_add:
            if entry.is_controller:
                remote.db_add_resp_of(self.addr, entry.group, entry.data,
                                      two_way, on_done)
            else:
                remote.db_add_ctrl_of(self.addr, entry.group, entry.data,
                                      two_way, on_done)

        # Delete command
        else:
            if entry.is_controller:
                remote.db_del_resp_of(self.addr, entry.group, entry.data,
                                      two_way, on_done)
            else:
                remote.db_del_ctrl_of(self.addr, entry.group, entry.data,
                                      two_way, on_done)

    #-----------------------------------------------------------------------
