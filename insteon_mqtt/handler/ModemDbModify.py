#===========================================================================
#
# Modem database modification (add/del) handler.
#
#===========================================================================
from .. import log
from .. import message as Msg
from .. import util
from .Base import Base

LOG = log.get_logger()


class ModemDbModify(Base):
    """Modem all link database modification handler.

    This handles message that arrive from adding, changing, or deleting
    records in the modem's all link database.  It will make the necessary
    modifications to the modem's all link database class to reflect what
    happened on the physical device.

    In many cases, a series of commands must be sent to the modem to change
    the database. So the handler can be passed future commands to send using
    add_update().  When a command is finished, the next command in the queue
    will be sent.  If any command fails, the sequence stops.
    """
    def __init__(self, modem_db, entry, existing_entry=None, on_done=None):
        """Constructor

        Args:
          modem_db (db.Modem):  The modem database being changed.
          entry (db.ModemEntry):  The new record or record being erased.
                This is the entry that the db will have if the command works.
          existing_entry (db.ModemEntry):  The existing database entry being
                         modified or None for a new or deleted record.
          on_done:  Finished callback.  This is called once for each call
                    added to the handler.  Signature is:
                    on_done(success, msg, entry)
        """
        super().__init__(on_done)

        self.db = modem_db
        self.entry = entry
        self.existing_entry = existing_entry

        # Tuple of (msg, entry) to send next.  If the first calls ACK's,
        # we'll update self.entry and send the next msg and continue until
        # this is empty.
        self.next = []

    #-----------------------------------------------------------------------
    def add_update(self, msg, entry):
        """Add a future call.

        The input message and entry will be sent after the current
        transaction completes successfully.

        Args:
          msg:  The next message to send.
          entry  (db.ModemEntry):  The new record or record being erased.
                 This is the entry that the db will have if the command works.
        """
        self.next.append((msg, entry))

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        This will update the modem's database if the command works.  Then the
        next message is written out.

        Args:
          protocol (Protocol):  The Insteon Protocol object
          msg:  Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.
        """
        # Not a message for us.
        if not isinstance(msg, Msg.OutAllLinkUpdate):
            return Msg.UNKNOWN

        # If we get a NAK message, signal an error and stop.
        if not msg.is_ack:
            LOG.error("Modem db updated failed: %s", msg)
            self.on_done(False, "Modem database update failed", self.entry)
            return Msg.FINISHED

        # ACK of a message to delete an existing entry
        if msg.cmd == Msg.OutAllLinkUpdate.Cmd.DELETE:
            LOG.info("Modem.delete removed entry: %s", self.entry)
            self.db.delete_entry(self.entry)

        # ACK of an Update an existing entry w/ new data fields.
        elif msg.cmd == Msg.OutAllLinkUpdate.Cmd.UPDATE:
            LOG.info("Updating modem db record for %s grp: %s data: %s",
                     msg.addr, msg.group, msg.data)

            assert self.existing_entry

            # Copy the data fields (they're the only thing that can be
            # updated) from the new entry to the existing entry and save the
            # db.  Since the existing entry is a handle to an entry in the
            # db, this works fine.
            self.existing_entry.data = self.entry.data
            self.db.save()

        # ACK of a new controller or responder.
        elif (msg.cmd == Msg.OutAllLinkUpdate.Cmd.ADD_CONTROLLER or
              msg.cmd == Msg.OutAllLinkUpdate.Cmd.ADD_RESPONDER):
            LOG.info("Adding modem db record for %s type: %s grp: %s data: %s",
                     msg.addr, util.ctrl_str(msg.db_flags.is_controller),
                     msg.group, msg.data)

            # This will also save the database.
            self.db.add_entry(self.entry)

        # Send the next database update message if we have any.
        if self.next:
            LOG.info("Sending next modem db update")
            msg, self.entry = self.next.pop(0)
            protocol.send(msg, self)

        # Only run the callback if this is the last message in the chain.
        else:
            self.on_done(True, "Modem database update complete", self.entry)

        return Msg.FINISHED

    #-----------------------------------------------------------------------
