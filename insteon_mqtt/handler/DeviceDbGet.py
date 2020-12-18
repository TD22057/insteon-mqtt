#===========================================================================
#
# Device get all link database handler.
#
#===========================================================================
# pylint: disable=too-many-return-statements
from .. import log
from .. import message as Msg
from .Base import Base

LOG = log.get_logger()


class DeviceDbGet(Base):
    """Device database request message handler.

    To download the all link database from a device, we send a request.  The
    output message gets ACK'ed back to us.  Then the device sends us a series
    of messages with the database entries.  The last message will be all
    zeros to indicate no more records.

    Each reply is passed to the callback function set in the constructor
    which is usually a method on the device to update it's database.
    """
    def __init__(self, device_db, on_done, num_retry=3, time_out=5):
        """Constructor

        The on_done callback has the signature on_done(success, msg, entry)
        and will be called with success=True if the handler finishes
        successfully or False if an error occurs or the handler times out.
        The message input is a string to help with logging the result.

        Args:
          device_db (db.Device):  The device database being retrieved.
          on_done:  Option finished callback.  This is called when the
                    handler is finished for any reason.
          num_retry (int):  The number of times to retry the message if the
                    handler times out without returning Msg.FINISHED.
                    This count does include the initial sending so a
                    retry of 3 will send once and then retry 2 more times.
                    Retries only apply to the initial get request and the ack
                    of that request.  The subsequent messages are streamed from
                    the device without further requests.  If the handler times
                    out after the initial request, there is no way to recover,
                    besides starting the request over again.
          time_out (int): Timeout in seconds.  The regular timeout applies to
                          the initial request.  The subsequent messages are
                          streamed from the device without further action.
                          Because the communication from this point on is
                          entirely one-sided coming from the device.  There is
                          nothing we can do from this end if a message fails to
                          arrive, so we keep the network as quiet as possible
                          by doubling the timeout.
        """
        super().__init__(on_done, num_retry, time_out)
        self.db = device_db

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        See if the message is the expected ACK of our output or the expected
        database reply message.  If we get a reply, pass it to the device to
        update it's database with the info.

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
        from .. import db  # pylint: disable=import-outside-toplevel

        # Probably an echo back of our sent message.  See if the message
        # matches the address we sent to and assume it's the ACK/NAK message.
        # These seem to be either extended or standard message so allow for
        # both.
        if isinstance(msg, (Msg.OutExtended, Msg.OutStandard)):
            if msg.to_addr == self.db.addr and msg.cmd1 == 0x2f:
                if not msg.is_ack:
                    LOG.warning("%s PLM NAK response", self.db.addr)
                return Msg.CONTINUE

            return Msg.UNKNOWN

        # Probably an ACK/NAK from the device for our get command.
        elif isinstance(msg, Msg.InpStandard):
            # Filter by address and command.
            if msg.from_addr != self.db.addr or msg.cmd1 != 0x2f:
                return Msg.UNKNOWN

            if msg.flags.type == Msg.Flags.Type.DIRECT_ACK:
                LOG.info("%s device ACK response", msg.from_addr)
                # From here on out, the device is the only one talking. So
                # remove any remaining retries, and double the timeout.
                self._num_retry = 0
                self._time_out = 2 * self._time_out
                return Msg.CONTINUE

            elif msg.flags.type == Msg.Flags.Type.DIRECT_NAK:
                if msg.cmd2 == msg.NakType.PRE_NAK:
                    # This is a "Pre NAK in case database search takes
                    # too long".  This happens when the device database is
                    # large.  Just ignore it, add more wait time and wait.
                    LOG.warning("%s Pre-NAK: %s, Message: %s", msg.from_addr,
                                msg.nak_str(), msg)
                    return Msg.CONTINUE
                else:
                    LOG.error("%s device NAK error: %s, Message: %s",
                              msg.from_addr, msg.nak_str(), msg)
                    self.on_done(False, "Database command NAK. " +
                                 msg.nak_str(), None)
                    return Msg.FINISHED

            else:
                LOG.warning("%s device unexpected msg: %s", msg.from_addr, msg)
                return Msg.UNKNOWN

        # Process the real reply.  Database reply is an extended messages.
        elif isinstance(msg, Msg.InpExtended):
            # Filter by address and command.
            if msg.from_addr != self.db.addr or msg.cmd1 != 0x2f:
                return Msg.UNKNOWN

            # Convert the message to a database device entry.
            entry = db.DeviceEntry.from_bytes(msg.data, db=self.db)
            LOG.ui("Entry: %s", entry)

            # Skip entries w/ a null memory location.
            if entry.mem_loc:
                self.db.add_entry(entry)

            # Note that if the entry is a null entry (all zeros), then
            # is_last_rec will be True as well.
            if entry.db_flags.is_last_rec:
                self.on_done(True, "Database received", entry)
                return Msg.FINISHED

            # Otherwise keep processing records as they arrive.
            else:
                return Msg.CONTINUE

        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
