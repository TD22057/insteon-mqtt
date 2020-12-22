#===========================================================================
#
# Modem search all link database handler.
#
#===========================================================================
from .. import log
from .. import message as Msg
from .. import util
from .Base import Base

LOG = log.get_logger()


class ModemDbSearch(Base):
    """PLM Modem database search message handler.

    This will handle a search command which tries to locate all entries that
    match the passed address and group but not is_controller or any data1-3
    values.  The search starts with an EXISTS command which finds the first
    matching entry if it exists.  Subsequent searches use the SEARCH cmd which
    finds the next entry.  In theory, there should only ever be a maximum of
    two matching entries (a controller and a responder).

    Commands are acked if the entry is found and nacked if not.

    After an ack, the entry will be returned in a seperate message. Each entry
    is added to the end of the modem class's database records.
    """
    def __init__(self, modem_db, on_done=None):
        """Constructor

        Args
          modem_db (db.Modem):  The database to update.
          entry (db.ModemEntry):  The entry being searched for.  is_controller
                                  will be ignored
          on_done:  The finished callback.  Calling signature:
                    on_done( bool success, str message, data )
        """
        super().__init__()

        self.db = modem_db
        self.on_done = util.make_callback(on_done)

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        See if the message is the expected ACK of our output or the expected
        database reply message.  If we get a reply, pass it to the modem
        database to update it's database with the info.

        Args:
          protocol (Protocol):  The Insteon Protocol object
          msg:  Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.
        """
        # Import here - at file scope this makes a circular import which is
        # ok in Python>=3.5 but not 3.4.
        from .. import db    # pylint: disable=import-outside-toplevel

        # Message is an ACK/NAK of the record request.
        if (isinstance(msg, (Msg.OutAllLinkUpdate)) and
                msg.cmd in (Msg.OutAllLinkUpdate.Cmd.EXISTS,
                            Msg.OutAllLinkUpdate.Cmd.SEARCH)):
            # If we get a NAK, then there are no more db records.
            if not msg.is_ack:
                LOG.info("Modem database search complete.")

                # Save the database to a local file.
                self.db.save()

                self.on_done(True, "Database search complete", None)
                return Msg.FINISHED

            # ACK - keep reading until we get the record we requested.
            return Msg.CONTINUE

        # Message is the record we requested.
        if isinstance(msg, Msg.InpAllLinkRec):
            LOG.info("Adding modem db record for %s grp: %s", msg.addr,
                     msg.group)
            # Create a modem database entry from the message data
            entry = db.ModemEntry(msg.addr, msg.group,
                                  msg.db_flags.is_controller, msg.data,
                                  db=self.db)
            if not msg.db_flags.in_use:
                # I don't think the modem will ever report unused entries
                LOG.info("Ignoring modem db record in_use = False")
            else:
                self.db.add_entry(entry)
                LOG.info("Entry: %s", entry)

            # Request the next record in the PLM database.
            LOG.info("Modem searching for next db record")
            db_flags = Msg.DbFlags.from_bytes(bytes(1))
            msg = Msg.OutAllLinkUpdate(Msg.OutAllLinkUpdate.Cmd.SEARCH,
                                       db_flags, entry.group, entry.addr,
                                       bytes(3))
            self.db.device.send(msg, self)

            # Return finished - this way the getnext message will go out.
            # We'll be used as the handler for that as well which repeats
            # until we get a nak response (handled above).
            return Msg.FINISHED

        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
