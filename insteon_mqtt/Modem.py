#===========================================================================
#
# Insteon modem class.
#
#===========================================================================
import json
import logging
import os
from . import db
from . import config
from .Address import Address
from . import handler
from . import message as Msg
from .Signal import Signal

LOG = logging.getLogger(__name__)


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
        self.devices = {}
        self.scenes = {}
        self.db = db.Modem()

        # Signal to emit when a new device is added.
        self.signal_new_device = Signal()  # emit(modem, device)

        # Add a generic read handler for any broadcast messages
        # initiated by the Insteon devices.
        msg_handler = handler.Broadcast(self)
        self.protocol.add_handler(msg_handler)

        # Handle user triggered factory reset of the modem.
        msg_handler = handler.Callback(Msg.InpUserReset, self.handle_reset)
        self.protocol.add_handler(msg_handler)

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

        # Read the device definitions and scenes.
        self.devices = self._load_devices(data.get('devices', []))
        self.scenes = self._load_scenes(data.get('scenes', []))

        # Send refresh messages to each device to check if the
        # database is up to date.
        if data.get('startup_refresh', False) is True:
            LOG.info("Starting device refresh")
            for device in self.devices.values():
                device.refresh()

    #-----------------------------------------------------------------------
    def get_db(self):
        """Load the all link database from the modem.

        This sends a message to the modem to start downloading the all
        link database.  The message handler handler.ModemGetDb is used to
        process the replies and update the modem database.
        """
        LOG.info("Modem sending get first db record command")

        # Request the first db record from the handler.  The handler
        # will request each next record as the records arrive.
        msg = Msg.OutAllLinkGetFirst()
        msg_handler = handler.ModemGetDb(self)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def db_path(self):
        """Return the all link database path.

        This will be the configuration save_path directory and the
        file name will be the modem hex address with a .json suffix.
        """
        return os.path.join(self.save_path, self.addr.hex) + ".json"

    #-----------------------------------------------------------------------
    def save_db(self):
        """Save the all link database to a file.

        The file is stored in JSON forma and has the path
        self.db_path().  If the save_path configuration input wasn't
        set, nothing is done.
        """
        if not self.save_path:
            return

        data = self.db.to_json()

        with open(self.db_path(), "w") as f:
            json.dump(data, f, indent=2)

        LOG.info("%s database saved %s entries", self.addr, len(self.db))

    #-----------------------------------------------------------------------
    def load_db(self):
        """Load the all link database from a file.

        The file is stored in JSON format (by save_db()) and has the
        path self.db_path().  If the file doesn't exist, nothing is
        done.
        """
        # See if the database file exists.
        path = self.db_path()
        if not os.path.exists(path):
            return

        # Read the file and convert it to a db.Modem object.
        try:
            with open(path) as f:
                data = json.load(f)

            self.db = db.Modem.from_json(data)
        except:
            LOG.exception("Error reading modem db file %s", path)
            return

        LOG.info("%s database loaded %s entries", self.addr, len(self.db))

    #-----------------------------------------------------------------------
    def add(self, device):
        """Add a device object to the modem.

        Args:
          device    The device object to add.
        """
        self.devices[device.addr.id] = device

    #-----------------------------------------------------------------------
    def remove(self, device):
        """Remove a device object from the modem.

        Args:
          device    The device object to add.  If the device doesn't exist,
                    nothing is done.
        """
        self.devices.pop(device.addr.id, None)

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
        if not isinstance(addr, Address):
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
        self.get_db()

        # Reload all the device databases.
        for device in self.devices.values():
            device.get_db()

    #-----------------------------------------------------------------------
    def add_controller_of(self, addr, group, data=None):
        """TODO: doc
        """
        cmd = Msg.OutAllLinkUpdate.ADD_CONTROLLER
        is_ctrl = True
        device_cmd = "add_responder_of"
        self._modify_db(cmd, is_ctrl, addr, group, device_cmd, data)

    #-----------------------------------------------------------------------
    def add_responder_of(self, addr, group, data=None):
        """TODO: doc
        """
        cmd = Msg.OutAllLinkUpdate.ADD_RESPONDER
        is_ctrl = False
        device_cmd = "add_controller_of"
        self._modify_db(cmd, is_ctrl, addr, group, device_cmd, data)

    #-----------------------------------------------------------------------
    def del_controller_of(self, addr, group):
        """TODO: doc
        """
        cmd = Msg.OutAllLinkUpdate.DELETE
        is_ctrl = True
        device_cmd = "del_responder_of"
        self._modify_db(cmd, is_ctrl, addr, group, device_cmd)

    #-----------------------------------------------------------------------
    def del_responder_of(self, addr, group):
        """TODO: doc
        """
        cmd = Msg.OutAllLinkUpdate.DELETE
        is_ctrl = False
        device_cmd = "del_controller_of"
        self._modify_db(cmd, is_ctrl, addr, group, device_cmd)

    #-----------------------------------------------------------------------
    def factory_reset(self):
        LOG.warning("Modem being reset.  All data will be lost")
        msg = Msg.OutResetPlm()
        msg_handler = handler.Callback(msg, self.handle_reset)
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
        """
        LOG.info("Modem command: %s", kwargs)

        cmd = kwargs.get('cmd', None)
        if not cmd:
            LOG.error("Invalid command sent to modem.  No 'cmd' keyword: %s",
                      kwargs)
            return

        if cmd == 'getdb':
            self.get_db()
        elif cmd == 'reload_all':
            self.reload_all()
        if cmd == 'factory_reset':
            self.factory_reset()
        else:
            LOG.error("Unknown modem command '%s'.  Valid commands are: "
                      "'getdb'", cmd)

    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        """Handle a broadcast message from the modem.

        The modem has no scenes that can be triggered by the modem so
        this should never be called.

        Args:
           msg:    (message.InpStandard) Broadcast group message.
        """
        pass

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
        # The modem mhas nothing to do for these messages.
        pass

    #-----------------------------------------------------------------------
    def handle_db_rec(self, msg):
        """New all link database record handler.

        This is called by the handler.ModemGetDb message handler when a
        new message.InpAllLinkRec message is read.  Each message is an
        entry in the modem's all link database.

        Args:
          msg:   (InpAllLinkRec).  None if there are no more messages in
                 which case the database is saved.  Otherwise the entry is
                 passed to the db.Modem database for addition.
        """
        # Last database record read.
        if msg is None:
            LOG.info("PLM modem database download complete:\n%s", str(self.db))

            # Save the database to a local file.
            self.save_db()

        # Add the record to the database.
        else:
            assert isinstance(msg, Msg.InpAllLinkRec)
            if not msg.flags.in_use:
                LOG.info("Ignoring modem db record in_use = False")
                return

            self.db.handle_db_rec(msg)

    #-----------------------------------------------------------------------
    def handle_reset(self, msg):
        """TODO: doc
        """
        assert isinstance(msg, (Msg.OutResetPlm, Msg.InpUserReset))

        if msg.is_ack:
            LOG.warning("Modem has been reset")
            self.db.clear()
            if os.path.exists(self.db_path()):
                os.path.erase(self.db_path())
        else:
            LOG.error("Modem factory reset failed")

    #-----------------------------------------------------------------------
    def _load_devices(self, data):
        """Load device definitions from a configuration data object.

        The input data object is a list of dictionaries.  Keys are the
        device type (see config.devices dict for valid entries).  The
        value is a dictionary of constructor arguments to pass to the
        device class.  This includes the insteon address of
        the device and any other inputs the class needs.

        [ {'on_off': {'address': 'a2.b3.c4', 'name': 'lamp'}},
          {'dimmer': {'address': 'a2.b3.c4', 'name': 'hallway'}},
          {'smoke_bridge': {'address': 'a2.b3.c4'}},
          {'remote8': {'address': 'a2.b3.c4', 'name': 'remote_01'}},
        ]

        Args:
          data:   Configuration data list.

        Returns:
          Returns a dictionary mapping Insteon addresses to device objects.
        """
        device_map = {}
        for device_dict in data:
            assert len(device_dict) == 1

            # Get the first key from the device dictionary.
            type = next(iter(device_dict))
            args = device_dict[type]

            # Look up the device type in the configuration data and
            # call the constructor to build the device object.
            ctor = config.find(type)
            device = ctor(**args, protocol=self.protocol, modem=self)
            LOG.info("Created %s at %s '%s'", device.__class__.__name__,
                     device.addr, device.name)

            # Load any existing all link database for this device if
            # it exists.
            if self.save_path:
                device.save_path = self.save_path
                device.load_db()

            # Store the device by ID in the map.
            device_map[device.addr.id] = device

            # Notify anyone else tha ta new device is available.
            self.signal_new_device.emit(self, device)

        return device_map

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
    def _modify_db(self, cmd, is_ctrl, addr, group, device_cmd, data=None):
        """TODO: doc
        """
        # Find the device the link is for.
        device = self.find(addr)
        if not device:
            # TODO???
            return

        # See if there is a current database entry for this
        # combination.  If there is, change the command to update
        # unless we're removing it.
        entry = self.db.find(addr, group, is_ctrl)
        if entry and cmd != Msg.OutAllLinkUpdate.DELETE:
            cmd = Msg.OutAllLinkUpdate.UPDATE

        # Build the modem database update message.
        flags = Msg.DbFlags(in_use=True, is_controller=is_ctrl, high_water=True)
        msg = Msg.OutAllLinkUpdate(cmd, flags, group, addr, data)

        # Modem will ack/nak our message.  This calls handle_db_update()
        # with the result.
        msg_handler = handler.ModemModifyDb(self)
        self.protocol.send(msg, msg_handler)

        # Send a message to the device to update it's end of the link.
        if device_cmd:
            func = getattr(device, device_cmd)
            func(self.addr, group, data)

    #-----------------------------------------------------------------------
    def handle_db_update(self, msg):
        """TODO: doc
        """
        # TODO: callback handler?  might be easier to understand.
        if msg.is_ack:
            LOG.info("Modem db updated: %s", msg)
            self.db.update_rec(msg)
            self.save_db()
        else:
            LOG.error("Modem db update error: %s", msg)

    #-----------------------------------------------------------------------
