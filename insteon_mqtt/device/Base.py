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

    The run_command() method is used for arbitrary remote commanding (via
    MQTT for example).  See the Base.cmd_map attribute for a list of methods
    tha can be called via run_command().  Derived types can extend that
    dictionary to add in their own commands to support.  Using a dictionary
    of the commands allows us to control access to which commands should be
    supported by remote access via MQTT.  If we just looked up the method
    names from the class, then anything could be called via remote message
    which isn't desirable.
    """
    @classmethod
    def from_config(cls, values, protocol, modem, **kwargs):
        """Load all the devices for a specific type from configuration.

        This is called by once for each device type (switch, dimmer, etc)
        that is read in the input configuration yaml file.  It loops over the
        device instances (names+Insteon addressses) and creates an instance
        of the cls type for each one.

        Args:
          cls:  The class type being loaded.  This will be the actual
                derived class type.
          values (list):  The list of configuration entries this device type.
          protocol (Protocol):  The protocol object to use.
          modem (Modem):  The Insteon Modem object to communicate with.
          kwargs:  Optional keyword arguments to pass to the class
                   constructor.

        Returns:
          [cls]:  Returns a list of the created device instances.
        """
        devices = []

        # Loop over the configuration data.
        for config in values:
            # If it's a dict, it's got a nice name set.
            if isinstance(config, dict):
                assert len(config) == 1
                addr, name = next(iter(config.items()))
                if name:
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

        This initializes common code for all the device types.  Derived types
        must call this in their constructors.

        Args:
          protocol (Protocol):  The Protocol object used to communicate
                   with the Insteon network.  This is needed to allow the
                   device to send messages to the PLM modem.
          modem (Modem):  The Insteon modem used to find other devices.
          address (Address):  The address of the device.
          name (str):  Nice alias name to use for the device.
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
        self.db = db.Device(self.addr, None, self)
        self.load_db()

        # Config db is initiated by Scenes
        self.db_config = None

        # Map (mqtt) commands mapped to methods calls.  These are handled in
        # run_command().  Derived classes can add more commands to the dict
        # to expand the list.  Commands should all be lower case (inputs are
        # lower cased).
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
            'get_model' : self.get_model,
            'sync': self.sync,
            'import_scenes': self.import_scenes
            }

        # Device database delta.  The delta tells us if the database is
        # current.  The only way to get this is by sending a refresh message
        # out and getting the response - not by downloading the database.
        self._next_db_delta = None

    #-----------------------------------------------------------------------
    def clear_db_config(self):
        """Clears and initializes the device config database
        """
        self.db_config = db.Device(self.addr, None, self)

    #-----------------------------------------------------------------------
    def type(self):
        """Return a nice class name for the device.

        Returns:
          str:  Returns the device class name in lower case ('dimmer').
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
          msg (Message):  Output message to write.  This should be an
              instance of a message in the message directory that that starts
              with 'Out'.
          msg_handler (MsgHander): Message handler instance to use when
                      replies to the message are received.  Any message
                      received after we write out the msg are passed to this
                      handler until the handler returns the message.FINISHED
                      flags.
          high_priority (bool):  False to add the message at the end of the
                        queue.  True to insert this message at the start of
                        the queue.
          after (float):  Unix clock time tag to send the message after.
                If None, the message is sent as soon as possible.  Exact time
                is not guaranteed - the message will be send no earlier than
                this.
        """
        if isinstance(msg, Msg.OutStandard):  # handles OutExtended as well
            msg.flags.set_hops(self.history.avg_hops())

        self.protocol.send(msg, msg_handler, high_priority, after)

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

            self.db = db.Device.from_json(data, path, self)
        except:
            LOG.exception("Error reading file %s", path)
            return

        LOG.info("Device %s database loaded %s entries", self.label,
                 len(self.db))
        LOG.debug("%s", self.db)

    #-----------------------------------------------------------------------
    def print_db(self, on_done):
        """Print the device database to the log UI.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
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

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Join Device %s", self.addr)

        # Using a sequence so we can pass the on_done function through.
        seq = CommandSeq(self.protocol, "Operation Complete", on_done)

        # First get the engine version.  This process only works and is
        # necessary on I2CS devices.
        seq.add(self.get_engine)

        # Then run the action joining command which checks to see if anything
        # further is needed.
        seq.add(self._join_device)

        seq.run()

    #-----------------------------------------------------------------------
    def _join_device(self, on_done=None):
        """Pair this device with the modem in both directions.

        This command is only required for I2CS devices.  This function is
        called after get_engine and will only perform a link sequence if the
        engine version requires it.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
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
        """Initiate linking mode on the device.

        This command tells the device to enter linking mode - we get ACK back
        that it did, but unlike the modem, we don't get a message telling us
        what the result is when the linking actually completes.  So there
        needs to be a refresh call made to the device once the linking
        actually finishes.

        This is normally used to link the device to and from the modem.  Once
        that's done, the db_add methods on the device should be used to create
        links to other devices.

        Args:
          group (int):  The group to link when something connects
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Device %s link mode grp %s", self.label, group)

        # This sends a linking mode command to the device.  As far as I can
        # see, there is no way to cancel it.
        msg = Msg.OutExtended.direct(self.addr, 0x09, group,
                                     bytes([0x00] * 14))
        msg_handler = handler.StandardCmd(msg, self.handle_linking, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def pair(self, on_done=None):
        """Pair the device with the modem.

        This only needs to be called one time.  It will set the device as a
        controller and the modem as a responder for all of the groups that
        the device can alert on.

        The default implementation does nothing - subclasses should
        re-implement this to do proper pairing.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.error("Device %s doesn't support pairing", self.label)

    #-----------------------------------------------------------------------
    def refresh(self, force=False, on_done=None):
        """Refresh the current device state and database if needed.

        This sends a ping to the device.  The reply has the current device
        state (on/off, level, etc) and the current db delta value which is
        checked against the current db value.  If the current db is out of
        date, it will trigger a download of the database.

        This will send out an updated signal for the current device status
        whenever possible (like dimmer levels).

        Args:
          force (bool):  If true, will force a refresh of the device database
                even if the delta value matches as well as a re-query of the
                device model information even if it is already known.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
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
        self.addRefreshData(seq, force)

        # Run all the commands.
        seq.run()

    #-----------------------------------------------------------------------
    def addRefreshData(self, seq, force=False):
        """Add commands to refresh any internal data required.

        The base class uses this update the device catalog ID's and firmware
        if we don't know what they are.

        This is split out of refresh() so derived classes that override
        refresh can also get this information.

        Args:
          seq (CommandSeq): The command sequence to add the command to.
          force (bool):  If true, will force a refresh of the device database
                even if the delta value matches as well as a re-query of the
                device model information even if it is already known.
        """
        # If model number is not known, or force true, run get_model
        if self.db.desc is None or self.db.firmware is None or force:
            seq.add(self.get_model)

    #-----------------------------------------------------------------------
    def get_flags(self, on_done=None):

        """Get the Insteon operational flags field from the device.

        The flags will be passed to the on_done callback as the data field.
        Derived types may do something with the flags by override the
        handle_flags method.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
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
        """Request the engine version of the device

        The engine version can be i1, i2, or i2cs.  The engine version
        defines what type of messages can be used with a device and the type
        of all link database used by a device.  The version will be passed to
        the callback as the data input.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Device %s cmd: get engine version", self.label)

        # Send the get_engine_version request.
        msg = Msg.OutStandard.direct(self.addr, 0x0D, 0x00)
        msg_handler = handler.StandardCmd(msg, self.handle_engine, on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def get_model(self, on_done=None):
        """Request the (dev_cat, sub_cat, and firmware) data from the device.

        The resulting fields are set into the device db (self.db) for storage
        and later use.

        Args:
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        LOG.info("Device %s cmd: get engine version", self.label)

        # Send the get_engine_version request.
        msg = Msg.OutStandard.direct(self.addr, 0x10, 0x00)
        msg_handler = handler.BroadcastCmdResponse(msg, self.handle_model,
                                                   on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def sync(self, dry_run=True, refresh=True, sequence=None, on_done=None):
        """Syncs the links on the device.

        This will add, remove, and fix links on the device to ensure that the
        device matches the links that are defined in the scenes config.

        WARNING: If you have no links defined in your scenes config, this will
        erase all links except the links created by the 'join' and 'pair'
        commands.

        It is recommended that you perform a 'dry_run' command first to
        see what changes would be made to this device.

        In the future an 'import_links' command will be added which will allow
        for manually created links to be added to the scenes config.

        Args:
          dry_run: (Boolean) Logs the actions that would be completed by the
                   'sync' command, but does not actually perform any actions.
                   Default: True
          refresh: (Boolean) performs a device refresh before syncing.
                   Default: True
          sequence: (CommandSeq) Sequence entries will be added onto this
                   sequence.  If None, will create and execute a new sequence.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        dry_run_text = ''
        if dry_run:
            dry_run_text = '- DRY RUN'
        on_done = util.make_callback(on_done)
        LOG.info("Device %s cmd: sync", self.label)

        # Prepare command sequence
        if sequence is not None:
            seq = sequence
        else:
            seq = CommandSeq(self.protocol, "Sync complete", on_done,
                             error_stop=False)

        if refresh:
            LOG.ui("Performing DB Refresh of %s device", self.label)
            seq.add(self.refresh)
            seq.add(self.sync, dry_run, refresh=False, sequence=sequence)
        else:
            LOG.ui("Syncing %s device %s", self.label, dry_run_text)
            # Perform diff after refresh if asked for
            diff = self.db_config.diff(self.db)

            if len(diff.del_entries) > 0 or len(diff.add_entries) > 0:
                for entry in diff.del_entries:
                    seq.add(self._sync_del, entry, dry_run)
                for entry in diff.add_entries:
                    seq.add(self._sync_add, entry, dry_run)
            else:
                LOG.ui("  No changes necessary.")

        if sequence is None:
            seq.run()
        else:
            on_done(True, "Sync Complete", None)

    def _sync_del(self, entry, dry_run, on_done=None):
        '''Deletes a link on the device with a Log UI Message

        Used by sync() so that messages are displayed in a logical fashion
        '''
        if dry_run:
            LOG.ui("  Would Delete %s:", entry)
            on_done(True, None, None)
        else:
            LOG.ui("  Deleting %s:", entry)
            self.db.delete_on_device(self, entry, on_done=on_done)

    def _sync_add(self, entry, dry_run, on_done=None):
        ''' Adds a link to the device with a Log UI Message

        Used by sync() so that messages are displayed in a logical fashion
        '''
        if dry_run:
            LOG.ui("  Would Add %s:", entry)
            on_done(True, None, None)
        else:
            LOG.ui("  Adding %s:", entry)
            self.db.add_on_device(self, entry.addr, entry.group,
                                  entry.is_controller, entry.data,
                                  on_done=on_done)

    def import_scenes(self, dry_run=True, save=True, on_done=None):
        """Imports Scenes Defined on the Device into the Scenes Config.

        Any scene present on the device, but not defined in the Scenes Config
        will be added to the Scenes Config.  This will only add definitions,
        it will not remove them.  It is overly optimistic and will add a
        scene even when only half the the link pair is defined as well as
        when a scene is linked to an unknown device.

        WARNING: There is no way to ensure that the newly created scenes
        match the style and formatting that you may have adopted for your
        Scenes Config file.

        It is recommended that you perform a 'dry_run' command first to
        see what changes would be made to Scenes Config.

        Args:
          dry_run: (Boolean) Logs the actions that would be completed by the
                   'import_scenes' command, but does not actually perform any
                   actions. Default: True
          save:    (Boolean) If true will save the resulting scenes to disk if
                    dry-run is also True.  Not meant to be used by a user, is
                    used by import_scenes_all.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
        """
        on_done = util.make_callback(on_done)
        dry_run_text = ''
        changes = False
        if dry_run:
            dry_run_text = '- DRY RUN'
        LOG.info("Device %s cmd: import_scenes", self.label)
        LOG.ui("Importing Scenes from %s device %s", self.label, dry_run_text)

        diff = self.db.diff(self.db_config)

        # Import only cares about adding entries, ignore deletes
        if len(diff.add_entries) > 0:
            LOG.ui("  Adding the following scenes %s:", dry_run_text)
            for entry in diff.add_entries:
                LOG.ui("    %s", entry)
                if not dry_run:
                    self.modem.scenes.add_or_update(self, entry)
                    changes = True
        else:
            LOG.ui("  No changes necessary.")
        if changes and save:
            self.modem.scenes.save()
        # No matter what, repopulate db_configs so that we can skip importing
        # the other half of a link
        self.modem.scenes.populate_scenes()
        LOG.ui("Import Scenes Done.")
        on_done(True, "Import Scenes Done.", None)

    #-----------------------------------------------------------------------
    def db_add_ctrl_of(self, local_group, remote_addr, remote_group,
                       two_way=True, refresh=True, on_done=None,
                       local_data=None, remote_data=None):
        """Add the device as a controller of another device.

        This updates the devices's all link database to show that the device
        is controlling another Insteon device.  If two_way is True, the
        corresponding responder link on the other device is also created.
        This two-way link is required for the other device to accept commands
        from this device.

        The 3 byte data entry is usually (on_level, ramp_rate, unused) where
        those values are 1 byte (0-255) values but those fields are device
        dependent.

        The optional callback has the signature:
            on_done(bool success, str message, entry)

        - success is True if both commands worked or False if any failed.
        - message is a string with a summary of what happened.  This is used
          for user interface responses to sending this command.
        - entry is the db.DeviceEntry that was updated.

        Args:
          local_group (int):  The device group to use as the scene number.
          remote_addr (Address):  The address of the device to control.
          remote_group (int):  The group on the remote address to control.
          two_way (bool):  If True, after creating the controller link on the
                  device, a responder link is created on the remote device
                  to form the required pair of entries.
          refresh (bool):  If True, call refresh before changing the db.
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
          local_data (bytes[3]):  The local 3 byte data array to set on the
                     this db entry.  If this is None, it will be assigned
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
        """Add the device as a responder of another device.

        This updates the devices's all link database to show that the device
        is responding to another Insteon device.  If two_way is True, the
        corresponding controller link on the other device is also created.
        This two-way link is required for the other device to accept commands
        from this device.

        The 3 byte data entry is usually (on_level, ramp_rate, unused) where
        those values are 1 byte (0-255) values but those fields are device
        dependent.

        The optional callback has the signature:
            on_done(bool success, str message, entry)

        - success is True if both commands worked or False if any failed.
        - message is a string with a summary of what happened.  This is used
          for user interface responses to sending this command.
        - entry is the db.DeviceEntry that was updated.

        Args:
          local_group (int):  The group to use as the scene number.
          remote_addr (Address):  The address of the device to respond to.
          remote_group (int):  The group on the remote address to respond to.
          two_way (bool):  If True, after creating the responder link on the
                  device, a controller link is created on the remote device
                  to form the required pair of entries.
          refresh (bool):  If True, call refresh before changing the db.
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
          local_data (bytes[3]):  The local 3 byte data array to set on the
                     device db entry.  If this is None, it will be assigned
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
        """Delete the device as a controller of another device.

        This updates the devices's all link database to remove a record where
        the device is controlling another device.  If two_way is True, the
        corresponding responder link on the device is also remove.

        The optional callback has the signature:
            on_done(bool success, str message, entry)

        - success is True if both commands worked or False if any failed.
        - message is a string with a summary of what happened.  This is used
          for user interface responses to sending this command.
        - entry is the db.DeviceEntry that was removed.

        If the requested record doesn't exist, it's considered an error and
        on_done is called with success=False.

        Args:
          addr (Address):  The remote device address to delete on the modem.
          group (int):  The group on the device to delete the link for.
          two_way (bool):  If True, after deleting the controller link on the
                  device, the responder link is deleted on the remote device
                  to clean up the pair of entries.
          refresh (bool):  If True, call refresh before changing the db.
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
        """
        # Call with is_controller=True
        self._db_delete(addr, group, True, two_way, refresh, on_done)

    #-----------------------------------------------------------------------
    def db_del_resp_of(self, addr, group, two_way=True, refresh=True,
                       on_done=None):
        """Delete the device as a responder of another device.

        This updates the device's all link database to remove a record where
        the modem is responding to another device.  If two_way is True, the
        corresponding controller link on the device is also remove.

        The optional callback has the signature:
            on_done(bool success, str message, entry)

        - success is True if both commands worked or False if any failed.
        - message is a string with a summary of what happened.  This is used
          for user interface responses to sending this command.
        - entry is the db.DeviceEntry that was removed.

        If the requested record doesn't exist, it's considered an error and
        on_done is called with success=False.

        Args:
          addr (Address):  The remote device address to delete on the modem.
          group (int):  The group on the device to delete the link for.
          two_way (bool):  If True, after deleting the responder link on the
                  device, the controller link is deleted on the remote device
                  to clean up the pair of entries.
          refresh (bool):  If True, call refresh before changing the db.
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
        """
        # Call with is_controller=False
        self._db_delete(addr, group, False, two_way, refresh, on_done)

    #-----------------------------------------------------------------------
    def link_data(self, is_controller, group, data=None):
        """Create default device 3 byte link data.

        This is the 3 byte field (D1, D2, D3) stored in the device database
        entry.  This varies by device type.  These "base" settings are present
        on on/off (non-dimming) devices.  This function can and should be
        overwritten by other specialized devices.

        For controllers, the default fields are:
           D1: number of retries (0x03)
           D2: unknown (0x00)
           D3: the group number on the local device (0x01)

        For responders, the default fields are:
           D1: on level for switches and dimmers (0xff)
           D2: ramp rate, not used on base devices (0x00)
           D3: the group number on the local device (0x01)

        Args:
          is_controller (bool):  True if the device is the controller, false
                        if it's the responder.
          group (int):  The group number of the controller button or the
                group number of the responding button.
          data (bytes[3]):  Optional 3 byte data entry.  If this is None,
               defaults are returned.  Otherwise it must be a 3 element list.
               Any element that is not None is replaced with the default.

        Returns:
          bytes[3]:  Returns a list of 3 bytes to use as D1,D2,D3.
        """
        # Most of this is from looking through Misterhouse bug reports.
        if is_controller:
            defaults = [0x03, 0x00, 0x01]

        # Responder data is always link dependent.  Since nothing was given,
        # assume the user wants to turn the device on (0xff).
        else:
            defaults = [0xff, 0x00, 0x01]

        # For each field, use the input if not -1, else the default.
        return util.resolve_data3(defaults, data)

    #-----------------------------------------------------------------------
    def link_data_to_pretty(self, is_controller, data):
        """Converts Link Data1-3 to Human Readable Attributes

        This takes a list of the data values 1-3 and returns a dict with
        the human readable attibutes as keys and the human readable values
        as values.

        For base devices, this doesn't do anything.  So the return values will
        simply match the passed values.  Howevever, this function is meant
        to be overridded by specialized devices, look at the dimmer module
        for an example.

        Args:
          is_controller (bool):  True if the device is the controller, false
                        if it's the responder.
          data (list[3]):  List of three data values.

        Returns:
          list[3]:  list, containing a dict of the human readable values
        """
        # For the base devices this does nothing
        return [{'data_1': data[0]}, {'data_2': data[1]}, {'data_3': data[2]}]

    #-----------------------------------------------------------------------
    def link_data_from_pretty(self, is_controller, data):
        """Converts Link Data1-3 from Human Readable Attributes

        This takes a dict of the human readable attributes as keys and their
        associated values and returns a list of the data1-3 values.

        For base devices, this doesn't do anything.  So the return values will
        simply match the passed values.  Howevever, this function is meant
        to be overridded by specialized devices, look at the dimmer module
        for an example

        Args:
          is_controller (bool):  True if the device is the controller, false
                        if it's the responder.
          data (dict[3]):  Dict of three data values.

        Returns:
          list[3]:  List of Data1-3 values
        """
        # For the base devices this does nothing
        data_1 = None
        if 'data_1' in data:
            data_1 = data['data_1']
        data_2 = None
        if 'data_2' in data:
            data_2 = data['data_2']
        data_3 = None
        if 'data_3' in data:
            data_3 = data['data_3']
        return [data_1, data_2, data_3]

    #-----------------------------------------------------------------------
    def run_command(self, **kwargs):
        """Run arbitrary commands.

        Commands are input as a dictionary:
          { 'cmd' : 'COMMAND', ...args }

        where COMMAND is the command name and any additional arguments to the
        command are other dictionary keywords.  To find the arguments to
        pass, see the method being called for it's argument list.  See the
        class docs for a list of valid commands.

        Derived types may add their own commands to the self.cmd_map
        dictionary for dispatch.
        """
        cmd = kwargs.pop('cmd', None)
        if not cmd:
            LOG.error("Invalid command sent to device %s.  No 'cmd' "
                      "keyword: %s", self.label, kwargs)
            return

        # Look up the command method name in the command map dictionary.
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
        """Receives incoming message notifications from protocol

        This is called for every standard and extended message that is read
        from the modem from this device.  This is only used to track the hop
        distance from the modem to each device and isn't used for general
        message handling.

        It extracts the number of hops that occurred and uses that to create
        a moving average of the distance to the device so that outbound
        messages can set the maximum hop value for the most efficient
        transfers.

        Args:
          msg (Msg.InpStandard, Msg.InpExtended):  The message that arrived.
        """
        self.history.add(msg)

    #-----------------------------------------------------------------------
    def handle_refresh(self, msg):
        """Handle replies to the refresh command.

        The refresh command reply will contain the current device state in
        cmd2 and this updates the device with that value.

        Args:
          msg (message.InpStandard):  The refresh message reply.  The current
              device state is in the msg.cmd2 field.
        """
        # Do nothing - derived types can override this if they have
        # state to extract and update.
        pass

    #-----------------------------------------------------------------------
    def handle_flags(self, msg, on_done):
        """Handle replies to the get_flags command.

        The refresh command reply will contain the current device state in
        cmd2 and this updates the device with that value.

        Args:
          msg (message.InpStandard):  The get_flags message reply.  The current
              flags are in msg.cmd2.
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
        """
        LOG.ui("Device %s operating flags: %s", self.addr,
               "{:08b}".format(msg.cmd2))
        on_done(True, "Operation complete", msg.cmd2)

    #-----------------------------------------------------------------------
    def handle_engine(self, msg, on_done):
        """Handle replies to the get engine command.

        The engine command reply will contain the device engine version in
        cmd2 and this updates the device with that value.

        Args:
          msg (message.InpStandard):  The engine message reply.  The engine
              version state is in the msg.cmd2 field.
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
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
          msg (message.InpStandard):  The id request broadcast response.
          on_done:  Finished callback.  This is called when the command has
                    completed.  Signature is: on_done(success, msg, data)
        """
        if msg.cmd1 == 0x01 or msg.cmd1 == 0x02:
            dev_cat, sub_cat = msg.to_addr.ids[0], msg.to_addr.ids[1]
            firmware = msg.to_addr.ids[2]
            self.db.set_info(dev_cat, sub_cat, firmware)
            LOG.ui("Device %s received model information: %s firmware: %#x",
                   self.addr, self.db.desc, firmware)
            on_done(True, "Operation complete", None)
        else:
            LOG.debug("Device %s get_model response with wrong cmd %s",
                      self.addr, msg.cmd1)
            on_done(False, "Operation failed - wrong cmd", None)

    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        """Handle broadcast messages from this device.

        The broadcast message from a device is sent when the device is
        triggered.  The message has the group ID in it.  We'll update the
        device state and look up the group in the all link database.  For
        each device that is in the group (as a reponsder), we'll call
        handle_group_cmd() on that device to trigger it.  This way all the
        devices in the group are updated to the correct values when we see
        the broadcast message.

        Args:
          msg (InpStandard): Broadcast message from the device.
        """
        group = msg.group

        responders = self.db.find_group(group)
        LOG.debug("Found %s responders in group %s", len(responders), group)
        LOG.debug("Group %s -> %s", group, [i.addr.hex for i in responders])

        # For each device that we're the controller of call it's handler for
        # the broadcast message.
        for elem in responders:
            device = self.modem.find(elem.addr)
            if device:
                LOG.info("%s broadcast to %s for group %s", self.label,
                         device.addr, group)
                device.handle_group_cmd(self.addr, msg)
            else:
                LOG.warning("%s broadcast - device %s not found", self.label,
                            elem.addr)

    #-----------------------------------------------------------------------
    def handle_group_cmd(self, addr, msg):
        """Respond to a group command for this device.

        This is called when this device is a responder to a scene.  The
        device should look up the responder entry for the group in it's all
        link database and update it's state accordingly.

        Args:
          addr (Address):  The device that sent the message.  This is the
               controller in the scene.
          msg (InpStandard):  Broadcast message from the device.  Use
              msg.group to find the group and msg.cmd1 for the command.
        """
        # Default implementation - derived classes should specialize this.
        LOG.info("Device %s ignoring group cmd - not implemented", self.label)

    #-----------------------------------------------------------------------
    def handle_linking(self, msg, on_done=None):
        """Respond to a linking command for this device.

        This is called when we get a response to the linking command.  It
        will trigger on_done with either a success or failure flag set.

        Args:
          msg (InpStandard):  The linking response message.
          on_done: Finished callback.  This is called when the command has
                   completed.  Signature is: on_done(success, msg, data)
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
        # Use the bytes() cast here so we can take a list as input.
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
        """Delete an entry in the device database.

        See db_add_ctrl_of() or db_add_resp_of() for docs.
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
