#===========================================================================
#
# Insteon Protocol class.  Parses PLM data and writes messages.
#
#===========================================================================
import collections
import enum
import time
from . import log
from . import message as Msg
from .Signal import Signal
#from . import util

LOG = log.get_logger()


class WriteStatus(enum.Enum):
    """Current status of the output write queue."""
    # Messages can be sent to the serial link for writing.
    READY_TO_WRITE = 0
    # Message has been queued in the serial link but hasn't been written yet.
    PENDING_WRITE = 1
    # Message has been written and we're processing replies.  When the
    # message handler says it's done, this will be cleared back to READY so
    # more messages can be written.
    WAIT_FOR_REPLY = 2


# Output message and handler stored together.
OutputMsg = collections.namedtuple('OutputMsg', ['msg', 'handler'])


class Protocol:
    """Insteon PLM protocol processing class.

    This class processes the byte stream that is being read from and written
    to the Insteon PLM modem.  It connects to a network/Serial link class
    which handles the actual reading and writing.

    For input, this class connects to the network.Serial class signals for
    data being read.  When data is read, it's added to a bytearray and then
    we search for 0x02 bytes which are the start of an Insteon message.
    After that, we look at the message type code byte and search for a
    message handler to handle the class.  There can be a set of read handlers
    that are always active for handling messages.

    If a message was written out, it also registers a handler with the
    message to write.  That write handler is checked first whenever a message
    comes back in until all the expected replies come in.  Then the write
    handler is removed and the next message in the write queue is sent.

    The types of messages we expected are:

    1) Replies from commands we send to the modem.  For a standard message (8
       bytes), we'll get a echo reply w/ ACK/NAK (9 bytes).  If this fails,
       we'll get a 2 byte NAK.  After the ACK, we'll probably also get
       further messages in.  If we don't wait for these and continue writing
       messages, the modem won't send them (but will ACK them).  So once we
       send a message, we need to know what the expected reply is going to be
       and wait for that.

    2) Inbound messages from modem when a device triggers and sends a message
       to the modem.  This will be an 11 byte standard message that's a
       broadcast or broadcast cleanup type message.

    3) Device database reading.  Reading remote db's from a device involves
       sending one command, getting an ACK, then reading a series of messages
       (1 per db entry) until we get a final message which ends the sequence.
    """
    def __init__(self, link):
        """Constructor

        Args:
          link (network.Link):  Network Serial link class to use to
               communicate with the PLM modem.
        """
        self.link = link

        # Forward poll() calls from the network link to ourselves.  That way
        # we can test for write message time outs periodically.
        self._linkPoll = self.link.poll
        self.link.poll = self._poll

        # Connect the link read/write signals to our callback methods.
        link.signal_read.connect(self._data_read)
        link.signal_wrote.connect(self._msg_written)

        # Message received signal.  Every read message is passed to this.
        self.signal_received = Signal()  # (Message)

        # Inbound message buffer.
        self._buf = bytearray()

        # List of messages to send.  These contain an OutputMsg object which
        # has the message and handler from oldest to newest.  The handlers
        # are used to process responses.  We have to wait until the handler
        # says that it's done receiving replies until we can send the next
        # message.  If we write to the modem before that, it basically
        # cancels the previous action.  The _write_status flag indicates what
        # state the [0] message is in during the write process.  Status of
        # READY_TO_WRITE indicates we can write to the serial link.  When we
        # send a message to the serial link, status will change to
        # PENDING_WRITE.  When the serial link actually sends out the
        # message, status is changed to WAIT_FOR_REPLY.  When the message
        # handler says that it's done processing replies, status is changed
        # back to READY_TO_WRITE and we can write, the [0] object is removed,
        # can we'll write any other messages in the queue.
        self._write_queue = []
        self._write_status = WriteStatus.READY_TO_WRITE

        # Set of possible message handlers to use.  These are handlers that
        # handle any message that isn't handled by an explicit write handler.
        # # write handler.
        self._read_handlers = []

        # This is a list of prior read messages that are checked against to
        # determine if a subsequent message is a duplicate and can be
        # ignored.  Message are removed when their expired time is exceeded.
        # Only InpStandard and InpExtended messsages are de-duplicated at
        # this time.
        self._read_history = []

        # List of Msg.Timed objects which store a message and a time at which
        # to send the message.  It will be sorted by send time.  These are
        # messages that should be sent after a certain time has passed.  The
        # _poll() call will this and push them onto the message queue when
        # the current time is after the message time.
        self._timed_messages = []

        # Next time that a message can be written.  When a message is read,
        # we wait until it's expiration time (which is set by the hop count)
        # until we send another message.  Sending messages before a message
        # could expire w/ Insteon is a good way to cancel previous command so
        # we try and avoid that.
        self._next_write_time = 0

    #-----------------------------------------------------------------------
    def add_handler(self, handler):
        """Add a universal message handler.

        These handlers can handle any message that shows up.  This is
        normally used for broadcast messages that originate on the network
        without us writing us commands.

        See the classes in the handler sub-package for examples.

        Args:
           handler:  Message handler class to add.
        """
        self._read_handlers.append(handler)

    #-----------------------------------------------------------------------
    def remove_handler(self, handler):
        """Remove a universal message handler.

        Args:
           handler:  Message handler to remove.  If this doesn't exist,
                     nothing is done.
        """
        self._read_handlers.pop(handler, None)

    #-----------------------------------------------------------------------
    def load_config(self, config):
        """Load a configuration dictionary.

        This gets passed to the network link (usually network.Serial object)
        to load any configuration for the modem connection.

        Args:
          config (dict): Configuration data to load.
        """
        self.link.load_config(config)

    #-----------------------------------------------------------------------
    def send(self, msg, msg_handler, high_priority=False, after=None):
        """Write a message to the PLM modem.

        If there are no other messages in the queue, the message gets written
        immediately.  Otherwise the message is added to the write queue and
        will be written after other messages are finished.

        The handler is responsible for reading replies.  Each handler returns
        message.UNKNOWN if it can't process the message, message.CONTINUE if
        the message was handled and more replies are expected, or
        message.FINISHED if the message was handled and no more replies are
        expected.

        Arg:
          msg:  Output message to write.  This should be an instance of a
                message in the message directory that that starts with 'Out'.
          msg_handler:  Message handler instance to use when replies to the
                        message are received.  Any message received after we
                        write out the msg are passed to this handler until
                        the handler returns the message.FINISHED flags.
          high_priority (bool):  False to add the message at the end of the
                        queue.  True to insert this message at the start of
                        the queue.  This is ignored in timed messages.
          after (float):  Unix clock time tag to send the message after. If
                None, the message is sent as soon as possible.  Exact time is
                not guaranteed - the message will be send no earlier than this.
        """
        # If the time is input, append the inputs to the timer list and sort
        # the list by the times field.
        if after is not None:
            timed = Msg.Timed(msg, msg_handler, high_priority, after)
            self._timed_messages.append(timed)
            self._timed_messages.sort(key=lambda i: i.time)
            return

        # Normal message queue.
        output = OutputMsg(msg, msg_handler)
        if not high_priority:
            self._write_queue.append(output)

        # High priority messages insert at the front of the queue.
        else:
            self._write_queue.insert(0, output)

        # If there are no existing messages that we're waiting to send or
        # processing replies for, send the message immediately.
        if self._write_status == WriteStatus.READY_TO_WRITE:
            self._send_next_msg()

    #-----------------------------------------------------------------------
    def _poll(self, t):
        """Periodic polling function.

        The network stack calls this periodically.  If we have message
        handler, we'll use this to check for a time out if the correct set of
        replies hasn't been received yet.

        Args:
           t (float):  Current Unix clock time tag.
        """
        # Call the link poll function in case it needs to do something.
        self._linkPoll(t)

        # See if any timed messages should sent.
        while self._timed_messages and self._timed_messages[0].is_active(t):
            timed = self._timed_messages.pop(0)
            LOG.info("Moving timer based message to queue: %s", timed.msg)
            timed.send(self)

        # If we're waiting for a reply, ask the write handler if it's past
        # the time out in which case we'll mark this message as finished and
        # move on.
        if (self._write_status == WriteStatus.WAIT_FOR_REPLY and
                self._write_queue[0].handler.is_expired(self, t)):
            self._write_finished()

    #-----------------------------------------------------------------------
    def _data_read(self, link, data):
        """PLM modem data read callback.

        This is called by the network loop when data is read from the modem.
        We'll add it to our read buffer and try to find any insteon messages
        that are in it.

        Args:
          link (network.Link): The serial connection that read the data.
          data (bytes): bytes: The data that was read.
        """
        # Append the read data to the inbound message buffer.
        self._buf.extend(data)

        # Keep processing until there are no more messages to handle.  There
        # must be at least 2 bytes so we can read the message type code.
        while len(self._buf) > 1:
            #LOG.debug("Searching message (len %d): %s... ",
            #               len(self._buf), util.to_hex(self._buf,20))

            # Find a message start token.  Note that this token could also
            # appear in the middle of a message so we can't be totally sure
            # it's a message until we try to parse it.  If there is no
            # starting token - we're probably reading at the start in the
            # middle of a message so just clear it and wait until we get a
            # start token.
            start = self._buf.find(0x02)
            if start == -1:
                LOG.debug("No 0x02 starting byte found - clearing")
                self._buf = bytearray()
                break

            # Move the buffer to the start token.  Make sure we still have at
            # lesat 2 bytes or wait for more to arrive.
            if start != 0:
                LOG.debug("0x02 found at byte %d - shifting", start)
                self._buf = self._buf[start:]
                if len(self._buf) < 2:
                    break

            # Messages are [0x02,TYPE] so find map the type code to the
            # message class we need to use to read it.
            msg_type = self._buf[1]
            msg_class = Msg.types.get(msg_type, None)
            if not msg_class:
                LOG.info("Skipping unknown message type %#04x", msg_type)
                self._buf = self._buf[2:]
                continue

            # See if we have enough bytes to read the message.  If not, wait
            # until more data is read.
            msg_size = msg_class.msg_size(self._buf)
            if len(self._buf) < msg_size:
                break

            # Read the message and move the buffer forward.
            try:
                msg = msg_class.from_bytes(self._buf)
            except:
                LOG.exception("Unknown message bytes sequence")
                # Skip the initial 0x02 - this way if we got a weird message
                # with a 0x02 in the message, we won't miss an actual message
                # by moving msg_size bytes forward which could be wrong.
                self._buf = self._buf[1:]
                continue

            self._buf = self._buf[msg_size:]
            LOG.info("Read %#04x: %s", msg_type, msg)

            if self._is_duplicate(msg):
                LOG.info("Ignored duplicate %s", msg)
            else:
                # And try to process the message using the handlers.
                self._process_msg(msg)

    #-----------------------------------------------------------------------
    def _is_duplicate(self, msg):
        """Check whether incomming message is a duplicate.

        Duplicate messages arise because there may be an excess number of
        hops used in the transmitted message.  There are also times where the
        duplicate of the exact same message with the same number of hops
        arives twice.  It is unclear what causes this, but it could result
        from the transition of a wired signal to wireless and back.

        Args:
          msg:   Insteon message object to process.

        Returns:
          bool: True if this is a duplicate message, false otherwise
        """
        if not isinstance(msg, Msg.InpStandard):  # Also matches InpExtended
            return False

        current = time.time()

        # Remove any expired messages first.
        self._remove_expired_read(current)

        # Update the next allowed write time based on the number of hops that
        # are remaining on the inbound message.
        self._next_write_time = msg.expire_time
        LOG.debug("Setting next write time: %f", self._next_write_time)

        # See if we have a duplicate message.
        if msg in self._read_history:
            return True
        else:
            self._read_history.append(msg)
            return False

    #-----------------------------------------------------------------------
    def _remove_expired_read(self, t):
        """Removes old messages from the input message history.

        Removes messages which have expired from the input message history.

        Args:
          t (float): The current time.
        """
        expired_idx = []

        # Find all the messages where the current time is after the message
        # expiration time.
        for i, msg in enumerate(self._read_history):
            if t > msg.expire_time:
                expired_idx.append(i)

        # Remove them in reverse order so that the list indices remain valid.
        for i in reversed(expired_idx):
            del self._read_history[i]

    #-----------------------------------------------------------------------
    def _process_msg(self, msg):
        """Process a read message by passing it to the handlers.

        If we wrote out a message, we'll try and use the message handler for
        that message first.  If not or if that handler doesn't understand the
        message, we'll pass it to the read handlers for processing.

        Args:
          msg:  Insteon message object to process.
        """
        # Send the general message received notification.
        self.signal_received.emit(msg)

        # If we have a write handler, then most likely the inbound message is
        # a reply to the write so see if it can handle the message.  If the
        # status is FINISHED, then the handler has seen all the messages it
        # expects. If it's CONTINUE, it processed the message but expects
        # more.  If it's UNKNOWN, the handler ignored that message.
        if self._write_queue:
            handler = self._write_queue[0].handler
            LOG.debug("Passing msg to write handler: %s", handler)
            status = handler.msg_received(self, msg)

            # Handler is finished.  Send the next outgoing message if one is
            # waiting.
            if status == Msg.FINISHED:
                LOG.debug("Write handler finished")
                self._write_finished()
                return

            # If this message was understood by the write handler, don't look
            # in the read handlers and update the write handlers time out
            # into the future.
            elif status == Msg.CONTINUE:
                handler.update_expire_time()
                return

            assert status == Msg.UNKNOWN

        # No write handler or the message didn't match what the handler
        # expects to see.  Try the regular read handler to see if they
        # understand the message.
        for handler in self._read_handlers:
            status = handler.msg_received(self, msg)

            # If the message was understood by this handler return.  This
            # limits us to one handler per message but that's probably ok.
            if status != Msg.UNKNOWN:
                return

        # No handler was found for the message.  Shift pass the ID code and
        # look for more messages.  This might be better by having a lookup by
        # msg ID->msg size and use that to skip the whole message.
        LOG.warning("No read handler found for message type %#04x: %s",
                    msg.msg_code, msg)

    #-----------------------------------------------------------------------
    def _write_finished(self):
        """Message written finished.

        This is called when the write message handler returns
        message.FINISHED which means all the expected replies have been read.
        The write handler is cleared and the next message in the queue is
        written.  It can also be called if the handler times out.
        """
        assert self._write_queue

        self._write_queue.pop(0)
        self._write_status = WriteStatus.READY_TO_WRITE

        if self._write_queue:
            self._send_next_msg()

    #-----------------------------------------------------------------------
    def _msg_written(self, link, data):
        """Message written callback.

        This is called by the network link when the message packet has been
        written to the modem.

        Args:
          link (network.Link):  Network Serial link class to use to
               communicate with the PLM modem.
          data (bytes): The data that was written to the link.
        """
        assert self._write_queue
        assert self._write_status == WriteStatus.PENDING_WRITE

        # Set the status to show that the [0] message in the queue was
        # written out.
        self._write_status = WriteStatus.WAIT_FOR_REPLY

        # Tell the handler that we've sent the message to update the current
        # time out time.
        out = self._write_queue[0]
        out.handler.sending_message(out.msg)

    #-----------------------------------------------------------------------
    def _send_next_msg(self):
        """Send the next message in the write queue.

        This grabs the first message in the queue and sets it into the
        write_data field for later processing of replies.
        """
        # Get the next output message and handler from the write queue.
        out = self._write_queue[0]
        msg_bytes = out.msg.to_bytes()

        LOG.info("Write message to modem: %s", out.msg)
        LOG.debug("Write bytes to modem: %s", msg_bytes)

        # Write the message to the PLM modem.  The message will only be sent
        # when the current time is after the next write time as tracked by
        # the link.
        self.link.write(msg_bytes, self._next_write_time)
        self._write_status = WriteStatus.PENDING_WRITE

    #-----------------------------------------------------------------------
