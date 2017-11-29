#===========================================================================
#
# Device all link database modification handler.
#
#===========================================================================
import logging
from .. import message as Msg
from .Base import Base

LOG = logging.getLogger(__name__)


class DeviceDbModify(Base):
    """TODO: doc

    This handles replies when we need to add, remove, or modify the
    all link database on the PLM Device.  An output OutAllLinkUpdate
    message is sent and the Device will ACK or NAK a reply back to
    indicate the result.

    The reply is passed to the Device.handle_db_update so it knows
    whether to store the updated result or not.
    """
    def __init__(self, db, entry, on_done):
        """Constructor

        TODO: doc
        Args
          Device:   (Device) The Insteon Device.
        """
        super().__init__()

        self.db = db
        self.entry = entry

        # Use the input callback or a dummy function (so we don't have
        # to check to see if the callback exists).
        self.on_done = on_done if on_done else lambda *x : x

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

        TODO

        See if the message is the expected ACK of our output.  If we
        get a reply, pass it to the Device to update it's database with
        the info.

        Args:
          protocol:  (Protocol) The Insteon Protocol object
          msg:       Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.

        """
        if isinstance(msg, Msg.OutExtended):
            # See if the message address matches our expected reply.
            if msg.to_addr == self.db.addr and msg.cmd1 == 0x2f:
                # ACK - command is ok - wait for ACK from device.
                if msg.is_ack:
                    return Msg.CONTINUE

                # NAK - device rejected command.
                else:
                    LOG.error("Device NAK of device db modify: %s", msg)
                    self.on_done(False, self.entry, "Device database update "
                                 "failed")
                    return Msg.FINISHED

        elif isinstance(msg, Msg.InpStandard):
            # See if the message address matches our expected reply.
            if msg.from_addr == self.db.addr and msg.cmd1 == 0x2f:
                # ACK = success, NAK = failure - either way this
                # transaction is complete.
                if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
                    # Entry could be new entry, and update to an
                    # existing entry, or an marked unused (deletion).
                    LOG.info("Updating entry: %s", self.entry)
                    self.db.add_entry(self.entry)

                    # Send the next database update message.
                    if self.next:
                        LOG.info("%s sending next db update", self.db.addr)
                        msg, self.entry = self.next.pop(0)
                        protocol.send(msg, self)

                    # Only run the done callback if this is the last
                    # message in the chain.
                    else:
                        self.on_done(True, self.entry, "Device database "
                                     "update complete")

                elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
                    LOG.error("%s db mod NAK: %s", self.db.addr, msg)
                    self.on_done(False, self.entry, "Device database failed")

                else:
                    LOG.error("%s db mod unexpected msg type: %s",
                              self.db.addr, msg)
                    self.on_done(False, self.entry, "Device database failed")

                return Msg.FINISHED

        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
