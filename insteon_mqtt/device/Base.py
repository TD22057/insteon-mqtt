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
        self.db = db.Device()

        # Remove (mqtt) commands mapped to methods calls.  These are
        # handled in run_command().  Derived classes can add more
        # commands to the dict to expand the list.  Commands should
        # all be lower case (inputs are lowered).
        self.cmd_map = {
            'getdb' : self.db_get,
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
    def save_db(self):
        """Save the all link database to a file.

        The file is stored in JSON forma and has the path
        self.db_path().  If the save_path attribute wasn't set,
        nothing is done.
        """
        data = self.db.to_json()

        with open(self.db_path(), "w") as f:
            json.dump(data, f, indent=2)

        LOG.info("Device %s database saved %s entries", self.addr,
                 len(self.db))

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

        try:
            with open(path) as f:
                data = json.load(f)
        except:
            LOG.exception("Error reading file %s", path)
            return

        self.db = db.Device.from_json(data)

        LOG.info("Device %s database loaded %s entries", self.addr,
                 len(self.db))
        LOG.debug(str(self.db))

    #-----------------------------------------------------------------------
    def db_get(self):
        """Load the all link database from the modem.

        This sends a message to the modem to start downloading the all
        link database.  The message handler handler.DeviceGetDb is
        used to process the replies and update the modem database.
        """
        # We need to get the current db delta so we know which
        # database we're getting.  So clear the current flag and then
        # do a refresh which will find the delta and then trigger a
        # download.
        self.db.clear_delta()
        self.refresh()

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

        msg = Msg.OutStandard.direct(self.addr, 0x19, 0x00)

        # The returned message command will be a data field so in this
        # case don't check it against our input when matching messages.
        msg_handler = handler.StandardCmd(msg, self.handle_refresh, cmd=-1)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def add_controller_of(self, addr, group, data=None):
        """TODO: doc
        """
        # TODO: set controller flags.

        # Find the first unused record in the database.  If prev_last
        # is set, then we're adding a new entry and we need to update
        # the old lsat entry at the same time.
        rec, prev_last = self.db.find_unused(addr, group, True, data)

        # TODO: move this to the database?

    #-----------------------------------------------------------------------
    def add_responder_of(self, addr, group, data=None):
        """TODO: doc
        """
        cmd = Msg.OutAllLinkUpdate.ADD_RESPONDER
        is_controller = False
        device_cmd = "add_controller_of"
        self._modify_db(cmd, is_controller, addr, group, device_cmd, data)

    #-----------------------------------------------------------------------
    def del_controller_of(self, addr, group):
        """TODO: doc
        """
        cmd = Msg.OutAllLinkUpdate.DELETE
        is_controller = True
        device_cmd = "del_responder_of"
        self._modify_db(cmd, is_controller, addr, group, device_cmd)

    #-----------------------------------------------------------------------
    def del_responder_of(self, addr, group):
        """TODO: doc
        """
        cmd = Msg.OutAllLinkUpdate.DELETE
        is_controller = False
        device_cmd = "del_controller_of"
        self._modify_db(cmd, is_controller, addr, group, device_cmd)

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

        This checks the device database delta against the current all
        link datatabase level.  If the database is out of date, a
        message is sent to request the new database from the device.

        Most derived devices should override this to handle the devie
        state an dthen call this method to check the all link
        database.

        Args:
          msg:  (message.InpStandard) The refresh message reply.
        """
        # All link database delta is stored in cmd1 so we if we have
        # the latest version.  If not, schedule an update.
        if self.db.is_current(msg.cmd1):
            return

        LOG.info("Device %s db out of date - refreshing", self.addr)

        # Clear the current database and store the db delta from cmd1.
        self.db.clear()
        self._next_db_delta = msg.cmd1

        # Request that the device send us all of it's database
        # records.  These will be streamed as fast as possible to us.
        msg = Msg.OutExtended.direct(self.addr, 0x2f, 0x00, bytes(14))
        msg_handler = handler.DeviceGetDb(self.addr, self.handle_db_rec)
        self.protocol.send(msg, msg_handler)

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
    def handle_db_rec(self, msg):
        """Handle reading an all link database entry.

        This is called with a series of messages (one per entry) and
        then None when the there are no more entries in the all link
        database.  At that point the device database is written out to
        disk.

        Arg:
          msg:   (message.Msg.InpExtended) Extended message that contains
                 the device database entry.  This is passed to
                 db.Device database to parse the message.
        """
        # New record - add it to the device database.
        if msg is not None:
            self.db.handle_db_rec(msg)

        # Finished - we have all the records.
        else:
            self.db.delta = self._next_db_delta
            self._next_db_delta = None

            LOG.info("%s database download complete\n%s", self.addr, self.db)
            self.save_db()

    #-----------------------------------------------------------------------
