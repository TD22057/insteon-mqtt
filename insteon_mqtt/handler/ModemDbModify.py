#===========================================================================
#
# Modem database modification (add/del) handler.
#
#===========================================================================
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
    def __init__(self, modem_db, entry, existing_entry=None):
        """Constructor

        TODO: doc
        Args
          protocol: (Protocol) The Insteon protocol object.
          callback: Callback function to pass database messages to or None
                    to indicate the end of the entries.
          time_out: (int) Time out in seconds.  If we don't get an
                    InpAllLinkComplete message in this time, we'll send a
                    cancel message to the modem to cancel the all link mode.
        """
        super().__init__()

        self.db = modem_db
        self.entry = entry
        self.existing_entry = existing_entry

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

            self.db.add_entry(self.entry)

        return Msg.FINISHED

    #-----------------------------------------------------------------------
