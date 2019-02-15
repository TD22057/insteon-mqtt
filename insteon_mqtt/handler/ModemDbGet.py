#===========================================================================
#
# Modem get all link database handler.
#
#===========================================================================
from .. import log
from .. import message as Msg
from .. import util
from .Base import Base

LOG = log.get_logger()


class ModemDbGet(Base):
    """PLM Modem database request message handler.

    To download the all link database from the PLM modem, we send a request.
    The output message gets ACK'ed back to us.  Then the modem sends us a
    single record.  After we receive the record, we send another message out
    requesting the next record, etc, etc until we get a NAK to indicate there
    are no more records.

    Each reply is used to update the modem class's database records.
    """
    def __init__(self, modem_db, on_done=None):
        """Constructor

        Args
          modem_db (db.Modem):  The database to update.
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
        from .. import db

        # Message is an ACK/NAK of the record request.
        if isinstance(msg, (Msg.OutAllLinkGetFirst, Msg.OutAllLinkGetNext)):
            # If we get a NAK, then there are no more db records.
            if not msg.is_ack:
                LOG.ui("Modem database download complete:\n%s", str(self.db))

                # Save the database to a local file.
                self.db.save()

                self.on_done(True, "Database download complete", None)
                return Msg.FINISHED

            # ACK - keep reading until we get the record we requested.
            return Msg.CONTINUE

        # Message is the record we requested.
        if isinstance(msg, Msg.InpAllLinkRec):
            LOG.info("Adding modem db record for %s grp: %s", msg.addr,
                     msg.group)
            if not msg.db_flags.in_use:
                LOG.info("Ignoring modem db record in_use = False")
            else:
                # Create a modem database entry from the message data and
                # write it into the database.
                entry = db.ModemEntry(msg.addr, msg.group,
                                      msg.db_flags.is_controller, msg.data)
                self.db.add_entry(entry)
                LOG.ui("Entry: %s", entry)

            # Request the next record in the PLM database.
            LOG.info("Modem requesting next db record")
            msg = Msg.OutAllLinkGetNext()
            protocol.send(msg, self)

            # Return finished - this way the getnext message will go out.
            # We'll be used as the handler for that as well which repeats
            # until we get a nak response (handled above).
            return Msg.FINISHED

        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
