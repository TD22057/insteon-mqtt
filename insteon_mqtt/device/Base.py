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
        msg_handler = handler.DeviceRefresh(self, msg, num_retry=3)
        self.protocol.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def db_get(self):
        """Load the all link database from the modem.

        This sends a refresh command to the device so we can get the
        current database delta value so we know which db we're
        downloading.  Then it sends a message to the device to start
        downloading the all link database.  The message handler
        handler.DeviceDbGet is used to process the replies and update
        the modem database.

        NOTE: Some devices that are plugged in (smoke bridge) seem to
        be pretty bad about replying and multiple tries may be
        necessary to actually get the database.
        """
        # We need to get the current db delta so we know which
        # database we're getting.  So clear the current flag and then
        # do a refresh which will find the delta and then trigger a
        # download.
        self.db.set_delta(None)
        self.refresh()

    #-----------------------------------------------------------------------
    def db_add_ctrl_of(self, addr, group, data=None, two_way=True,
                       on_done=None):
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
            on_done(bool success, entry, str message)

        - success is True if both commands worked or False if one failed.
        - entry is either the db.ModemEntry or db.DeviceEntry that was
          updated.
        - message is a string with a summary of what happened.  This is used
          for user interface responses to sending this command.

        Args:
          addr:     (Address) The remote device address.
          group:    (int) The group to add link for.
          data:     (bytes[3]) 3 byte data entry.
          two_way:  (bool) If True, after creating the controller link on the
                    device, a responder link is created on the remote device
                    to form the required pair of entries.
          on_done:  Optional callback run when both commands are finished.
        """
        self._db_update(addr, group, data, two_way, is_controller=True,
                        on_done=on_done)

    #-----------------------------------------------------------------------
    def db_add_resp_of(self, addr, group, data=None, two_way=True,
                       on_done=None):
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
            on_done(bool success, entry, str message)

        - success is True if both commands worked or False if one failed.
        - entry is either the db.ModemEntry or db.DeviceEntry that was
          updated.
        - message is a string with a summary of what happened.  This is used
          for user interface responses to sending this command.

        Args:
          addr:     (Address) The remote device address.
          group:    (int) The group to add link for.
          data:     (bytes[3]) 3 byte data entry.
          two_way:  (bool) If True, after creating the responder link on the
                    device, a controller link is created on the remote device
                    to form the required pair of entries.
          on_done:  Optional callback run when both commands are finished.

        """
        self._db_update(addr, group, data, two_way, is_controller=False,
                        on_done=on_done)

    #-----------------------------------------------------------------------
    def db_del_ctrl_of(self, addr, group, two_way=True, on_done=None):
        """TODO: doc
        """
        self._db_delete(self, addr, group, two_way, is_controller=True,
                        on_done=on_done)

    #-----------------------------------------------------------------------
    def db_del_resp_of(self, addr, group, two_way=True, on_done=None):
        """TODO: doc
        """
        self._db_delete(self, addr, group, two_way, is_controller=False,
                        on_done=on_done)

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
    def _db_update(self, addr, group, data, two_way, is_controller, on_done):
        """Update the device database.

        See db_add_ctrl_of() or db_add_resp_of() for docs.
        """
        # Find the remote device.  If don't have an entry for this
        # device, we can't sent it commands
        remote = self.modem.find(addr)
        if two_way and not remote:
            lbl = "CTRL" if is_controller else "RESP"
            LOG.info("Device db add %s can't find remote device %s.  "
                     "Link will be only one direction", lbl, addr)

        # For two way commands, insert a callback so that when the
        # modem command finishes, it will send the next command to the
        # device.  When that finishes, it will run the input callback.
        use_cb = on_done
        if two_way and remote:
            use_cb = functools.partial(self._db_update_remote, remote, on_done)

        # Create a new database entry for the device and send it.
        self.db.add_on_device(self.protocol, addr, group, data, is_controller,
                              on_done=use_cb)

    #-----------------------------------------------------------------------
    def _db_update_remote(self, remote, on_done, success, entry, msg):
        """Device update complete callback.

        This is called when the device finishes updating the database.
        It triggers a corresponding call on the remote device to
        establish the two way link.  This only occurs if the first
        command works.
        """
        # If the command failed, just call the input callback.
        if not success:
            if on_done:
                on_done(success, entry, msg)
            return

        # Send the command to the device.  Two way is false here since
        # we just added the other link.
        two_way = False
        if entry.is_controller:
            remote.db_add_resp_of(self.addr, entry.group, entry.data, two_way,
                                  on_done)

        else:
            remote.db_add_ctrl_of(self.addr, entry.group, entry.data, two_way,
                                  on_done)

    #-----------------------------------------------------------------------
    def _db_delete(self, addr, group, two_way, is_controller, on_done):
        entry = self.db.find(addr, group, is_controller)
        if not entry:
            LOG.warning("Device %s delete no match for %s grp %s %s",
                        self.addr, addr, group,
                        'CTRL' if is_controller else 'RESP')
            if on_done:
                on_done(False, None, "Entry doesn't exist")
            return

        # Find the remote device.  If don't have an entry for this
        # device, we can't sent it commands
        remote = self.modem.find(addr)
        if two_way and not remote:
            lbl = "CTRL" if is_controller else "RESP"
            LOG.info("Device db delete %s can't find remote device %s.  "
                     "Link will be only one direction", lbl, addr)

        # For two way commands, insert a callback so that when the
        # modem command finishes, it will send the next command to the
        # device.  When that finishes, it will run the input callback.
        use_cb = on_done
        if two_way and remote:
            use_cb = functools.partial(self._db_delete_remote, remote, on_done)

        self.db.delete_on_device(self.protocol, self.addr, entry, on_done)

    #-----------------------------------------------------------------------
    def _db_delete_remote(self, remote, on_done, success, entry, msg):
        # If the command failed, just call the input callback.
        if not success:
            if on_done:
                on_done(success, entry, msg)
            return

        # Send the command to the device.  Two way is false here since
        # we just added the other link.
        two_way = False
        if entry.is_controller:
            remote.db_del_resp_of(self.addr, entry.group, entry.data, two_way,
                                  on_done)

        else:
            remote.db_del_ctrl_of(self.addr, entry.group, entry.data, two_way,
                                  on_done)

    #-----------------------------------------------------------------------
