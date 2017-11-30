#===========================================================================
#
# Modem database modification (add/del) handler.
#
#===========================================================================
import functools
import logging
from .. import message as Msg
from .Base import Base

LOG = logging.getLogger(__name__)


class ModemDbModify(Base):
    """TODO: doc


    This is used when the modem is placed in all-link mode (like
    pressing the set button).  We expect to get an ACK of the
    OutAllLinkStart message first.  If the all link mode is canceled,
    we'll get an OutAllLinkCancel ACK.  If linking completes (a device
    set button is held down to finish the link), we'll get an
    InpAllLinkComplete message

    If no reply is received in the time out window, we'll send an
    OutAllLinkCancel message.
    """
    def __init__(self, modem_db, entry, existing_entry=None, on_done=None):
        """Constructor

        TODO: doc
        Args
          protocol: (Protocol) The Insteon protocol object.
          callback: Callback function to pass database messages to or None
                    to indicate the end of the entries.
          time_out: (int) Time out in seconds.  If we don't get an
                    InpAllLinkComplete message in this time, we'll send a
                    cancel message to the modem to cancel the all link mode.
          on_done:  Callback to call when finished.
        """
        # Use the input callback or a dummy function (so we don't have
        # to check to see if the callback exists).  Pass the callback
        # to the base class constructor so that the time out code in
        # the base class can also call the handler if we time out.
        # Wrap the input to add the extra argument beyond the standard
        # on_done callback.
        if on_done:
            cb = functools.partial(on_done, entry=entry)
        else:
            cb = lambda *x: x
        super().__init__(on_done=cb)

        self.db = modem_db
        self.entry = entry
        self.existing_entry = existing_entry

        # Tuple of (msg, entry) to send next.  If the first calls
        # ACK's, we'll update self.entry and send the next msg and
        # continue until this is empty.
        self.next = []

    #-----------------------------------------------------------------------
    def add_update(self, msg, entry):
        """TODO: doc
        """
        self.next.append((msg, entry))

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        If all linking is finished, pass the message to the callback
        to update the device records (or re-download the database) if
        needed.

        Args:
          protocol:  (Protocol) The Insteon Protocol object
          msg:       Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.
        """
        if not isinstance(msg, Msg.OutAllLinkUpdate):
            return Msg.UNKNOWN

        if not msg.is_ack:
            LOG.error("Modem db updated failed: %s", msg)
            self.on_done(False, "Modem database update failed")
            return Msg.FINISHED

        # Delete an existing entry
        if msg.cmd == Msg.OutAllLinkUpdate.Cmd.DELETE:
            LOG.info("Modem.delete removed entry: %s", self.entry)
            self.db.delete_entry(self.entry)

        # Update an existing entry w/ new data fields.
        elif msg.cmd == Msg.OutAllLinkUpdate.Cmd.UPDATE:
            LOG.info("Updating modem db record for %s grp: %s data: %s",
                     msg.addr, msg.group, msg.data)

            assert self.existing_entry

            # Copy the data fields (they're the only thing that can be
            # updated) from the new entry to the existing entry and
            # save the db.  Since the existing entry is a handle to an
            # entry in the db, this works fine.
            self.existing_entry.data = self.entry.data
            self.db.save()

        # New controller or responder.
        elif (msg.cmd == Msg.OutAllLinkUpdate.Cmd.ADD_CONTROLLER or
              msg.cmd == Msg.OutAllLinkUpdate.Cmd.ADD_RESPONDER):
            LOG.info("Adding modem db record for %s type: %s grp: %s data: %s",
                     msg.addr, 'CTRL' if msg.db_flags.is_controller else
                     'RESP', msg.group, msg.data)

            # This will also save the database.
            self.db.add_entry(self.entry)

        # Send the next database update message.
        if self.next:
            LOG.info("Sending next modem db update")
            msg, self.entry = self.next.pop(0)
            protocol.send(msg, self)

        # Only run the done callback if this is the last message in
        # the chain.
        else:
            self.on_done(True, "Modem database update complete")

        return Msg.FINISHED

    #-----------------------------------------------------------------------
