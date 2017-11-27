#===========================================================================
#
# Base device class
#
#===========================================================================
import json
import logging
import os.path
from ..Address import Address
from .. import db
from .. import handler
from .. import message as Msg

LOG = logging.getLogger(__name__)


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
    def __init__(self, protocol, modem, address, name):
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
        self.save_path = None  # set by the modem loading method
        self.db = db.Device(self.addr)

        # Remove (mqtt) commands mapped to methods calls.  These are
        # handled in run_command().  Derived classes can add more
        # commands to the dict to expand the list.  Commands should
        # all be lower case (inputs are lowered).
        self.cmd_map = {
            'db_add_ctrl' : self.db_add_ctrl_of,
            'db_add_resp' : self.db_add_resp_of,
            'db_del_ctrl' : self.db_del_ctrl_of,
            'db_del_resp' : self.db_del_resp_of,
            'db_get' : self.db_get,
            'refresh' : self.refresh,
            }

        # Device database delta.  The delta tells us if the database
        # is current.  The only way to get this is by sending a
        # refresh message out and getting the response - not by
        # downloading the database.
        self._next_db_delta = None

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
        # See if the database file exists.
        path = self.db_path()
        self.db.set_path(path)
        if not os.path.exists(path):
            return

        try:
            with open(path) as f:
                data = json.load(f)

            self.db = db.Device.from_json(data, path)
        except:
            LOG.exception("Error reading file %s", path)
            return

        LOG.info("Device %s database loaded %s entries", self.addr,
                 len(self.db))
        LOG.debug("%s", self.db)

    #-----------------------------------------------------------------------
    def refresh(self):
        """Refresh the current device state and database if needed.

        This sends a ping to the device.  The reply has the current
        device state (on/off, level, etc) and the current db delta
        value which is checked against the current db value.  If the
        current db is out of date, it will trigger a download of the
        database.

        This will send out an updated signal for the current device
        status whenever possible (like dimmer levels).
        """
        LOG.info("Device %s cmd: status refresh", self.addr)

        # This sends a refresh ping which will respond w/ the current
        # database delta field.  The handler checks that against the
        # current value.  If it's different, it will send a database
        # download command to the device to update the database.
        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x00)
        msg_handler = handler.DeviceRefresh(self)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def db_get(self):
        """Load the all link database from the modem.

        This sends a message to the modem to start downloading the all
        link database.  The message handler handler.DeviceDbGet is
        used to process the replies and update the modem database.
        """
        # We need to get the current db delta so we know which
        # database we're getting.  So clear the current flag and then
        # do a refresh which will find the delta and then trigger a
        # download.
        self.db.set_delta(None)
        self.refresh()

    #-----------------------------------------------------------------------
    def db_add_ctrl_of(self, addr, group, data=None, force=False,
                       two_way=True):
        """TODO: doc
        """
        # Insure types are ok - this way strings passed in from JSON
        # or MQTT get converted to the type we expect.
        addr = Address(addr)
        group = int(group)
        data = data if data else bytes(3)

        remote = self.modem.find(addr)
        if two_way and not remote:
            if force:
                LOG.info("Device.db_add_ctrl_of can't find remote device %s.  "
                         "Link will be only one direction", addr)
            else:
                LOG.error("Modem.db_add_ctrl_of can't find remote device %s.  "
                          "Link cannot be added", addr)
                return

        self.db.add_on_device(self.protocol, self.addr, addr, group, data,
                              is_controller=True)

        if two_way and remote:
            remote.db_add_resp_of(self.addr, group, data, two_way=False)

    #-----------------------------------------------------------------------
    def db_add_resp_of(self, addr, group, data=None, force=False,
                       two_way=True):
        """TODO: doc
        """
        # Insure types are ok - this way strings passed in from JSON
        # or MQTT get converted to the type we expect.
        addr = Address(addr)
        group = int(group)
        data = data if data else bytes(3)

        remote = self.modem.find(addr)
        if two_way and not remote:
            if force:
                LOG.info("Device.db_add_resp_of can't find remote device %s.  "
                         "Link will be only one direction", addr)
            else:
                LOG.error("Modem.db_add_resp_of can't find remote device %s.  "
                          "Link cannot be added", addr)
                return

        self.db.add_on_device(self.protocol, self.addr, addr, group, data,
                              is_controller=False)

        if two_way and remote:
            remote.db_add_ctrl_of(self.addr, group, data, two_way=False)

    #-----------------------------------------------------------------------
    def db_del_ctrl_of(self, addr, group, force=False, two_way=True):
        """TODO: doc
        """
        # Insure types are ok - this way strings passed in from JSON
        # or MQTT get converted to the type we expect.  if the record
        # doesn't exist, don't do anything.
        entry = self.db.find(Address(addr), int(group), is_controller=True)
        if not entry:
            LOG.warning("Device %s delete no match for %s grp %s CTRL",
                        self.addr, addr, group)
            return

        self.db.delete_on_device(self.protocol, self.addr, entry)

        # TODO: find remote and delete entry there as well.

    #-----------------------------------------------------------------------
    def db_del_resp_of(self, addr, group, force=False, two_way=True):
        """TODO: doc
        """
        # Insure types are ok - this way strings passed in from JSON
        # or MQTT get converted to the type we expect.  if the record
        # doesn't exist, don't do anything.
        entry = self.db.find(Address(addr), int(group), is_controller=False)
        if not entry:
            LOG.warning("Device %s delete no match for %s grp %s RESP",
                        self.addr, addr, group)
            return

        self.db.delete_on_device(self.protocol, self.addr, entry)

        # TODO: find remote and delete entry there as well.

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
            LOG.error("Invalid command sent to device %s '%s'.  No 'cmd' "
                      "keyword: %s", self.addr, self.name, kwargs)
            return

        cmd = cmd.lower().strip()
        func = self.cmd_map.get(cmd, None)
        if not func:
            LOG.error("Invalid command sent to device %s '%s'.  Input cmd "
                      "'%s' not valid.  Valid commands: %s", self.addr,
                      self.name, cmd, self.cmd_map.keys())
            return

        # Call the command function with any remaining arguments.
        try:
            func(**kwargs)
        except:
            LOG.exception("Invalid command inputs to device %s '%s'.  Input "
                          "cmd %s with args: %s", self.addr, self.name, cmd,
                          str(kwargs))

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
        responders = self.db.find_group(msg.group)
        LOG.debug("Found %s responders in group %s", len(responders),
                  msg.group)
        LOG.debug("Group %s -> %s", msg.group,
                  [i.addr.hex for i in responders])

        # For each device that we're the controller of call it's
        # handler for the broadcast message.
        for elem in responders:
            device = self.modem.find(elem.addr)
            if device:
                LOG.info("%s broadcast to %s for group %s", self.addr,
                         device.addr, msg.group)
                device.handle_group_cmd(self.addr, msg)
            else:
                LOG.warning("%s broadcast - device %s not found", self.addr,
                            elem.addr)

    #-----------------------------------------------------------------------
    def handle_group_cmd(self, addr, msg):
        """Respond to a group command for this device.

        This is called when this device is a responder to a scene.
        The device should look up the responder entry for the group in
        it's all link database and update it's state accordingly.

        Args:
          addr:  (Address) The device that sent the message.  This is the
                 controller in the scene.
          msg:   (message.InpStandard) The broadcast message that was sent.
                 Use msg.group to find the scene group that was broadcast.
        """
        # Default implementation - derived classes should specialize this.
        LOG.info("Device %s ignoring group cmd - not implemented", self.addr)

    #-----------------------------------------------------------------------
