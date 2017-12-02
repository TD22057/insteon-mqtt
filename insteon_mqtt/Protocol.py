#===========================================================================
#
# Insteon Protocol class.  Parses PLM data and writes messages.
#
#===========================================================================
from . import log
from . import message as Msg

LOG = log.get_logger()


class Protocol:
    """Insteon PLM protocol processing class.

    This class processes the byte stream that is being read from and
    written to the Insteon PLM modem.  It connects to a network/Serial
    link class which handles the actual reading and writing.

    For input, this class connects to the network.Serial class signals
    for data being read.  When data is read, it's added to a bytearray
    and then we search for 0x02 bytes which are the start of an
    Insteon message.  After that, we look at the message type code
    byte and search for a message handler to handle the class.  There
    can be a set of read handlers that are always active for handling
    messages.

    If a message was written out, it also registers a handler with the
    message to write.  That write handler is checked first whenever a
    message comes back in until all the expected replies come in.
    Then the write handler is removed and the next message in the
    write queue is sent.

    The types of messages we expected are:

    1) Replies from commands we send to the modem.  For a standard
       message (8 bytes), we'll get a echo reply w/ ACK/NAK (9 bytes).
       If this fails, we'll get a 2 byte NAK.  After the ACK, we'll
       probably also get further messages in.  If we don't wait for
       these and continue writing messages, the modem won't send them
       (but will ACK them).  So once we send a message, we need to
       know what the expected reply is going to be and wait for that.

    2) Inbound messages from modem when a device triggers and sends a
       message to the modem.  This will be an 11 byte standard message
       that's a broadcast or broadcast cleanup type message.

    3) Device database reading.  Reading remote db's from a device
       involves sending one command, getting an ACK, then reading a
       series of messages (1 per db entry) until we get a final
       message which ends the sequence.
    """
    def __init__(self, link):
        """Constructor

        Args:
          link:   (network.Link) Network Serial link class to use to
                  communicate with the PLM modem.
        """
        self.link = link

        # Forward poll() calls from the network link to ourselves.
        # That way we can test for write message time outs periodically.
        self.link.poll = self._poll

        # Connect the link read/write signals to our callback methods.
        link.signal_read.connect(self._data_read)
        link.signal_wrote.connect(self._msg_written)

        # Inbound message buffer.
        self._buf = bytearray()

        # List of messages to send.  These contain a tuple of (msg,
        # handler) Messages from oldest to newest.  The handlers are
        # used to process responses.  We have to wait until the
        # handler says that it's done receiving replies until we can
        # send the next message.  If we write to the modem before
        # that, it basically cancels the previous action.  When a
        # message is written, it's handler object gets set into
        # _write_handler until that handler says that's received all
        # the expected replies (or times out).  At that point we'll
        # write the next message in the queue.
        self._write_queue = []

        # handler.Base message handler of the last written message.
        self._write_handler = None

        # Set of possible message handlers to use.  These are handlers
        # that handle any message besides the replies expected by the
        # write handler.
        self._read_handlers = []

        # TODO: add message deduplication.
        #    - Store last message and time tag
        #    - add __eq__ check to messages (or to store bytes?)
        #    - if no handler, arrival time near time tag, and same msg, ignore

    #-----------------------------------------------------------------------
    def add_handler(self, handler):
        """Add a universal message handler.

        These handlers can handle any message that shows up.  This is
        normally used for broadcast messages that originate on the
        network without us writing us commands.

        See the classes in the handler sub-package for examples.

        Args:
           handler:   (handler) Message handler class to add.
        """
        self._read_handlers.append(handler)

    #-----------------------------------------------------------------------
    def remove_handler(self, handler):
        """Remove a universal message handler.

        Args:
           handler:   (handler) Message handler to remove.  If this doesn't
                      exist, nothing is done.
        """
        self._read_handlers.pop(handler, None)

    #-----------------------------------------------------------------------
    def load_config(self, config):
        """Load a configuration dictionary.

        This gets passed to the network link (usually network.Serial
        object) to load any configuration for the modem connection.

        Args:
          config:   (dict) Configuration data to load.
        """
        self.link.load_config(config)

    #-----------------------------------------------------------------------
    def send(self, msg, msg_handler, high_priority=False):
        """Write a message to the PLM modem.

        If there are no other messages in the queue, the message gets
        written immediately.  Otherwise the message is added to the
        write queue and will be written after other messages are
        finished.

        The handler is responsible for reading replies.  Each handler
        returns message.UNKNOWN if it can't process the message,
        message.CONTINUE if the message was handled and more replies
        are expected, or message.FINISHED if the message was handled
        and no more replies are expected.

        Arg:
          msg:            Output message to write.  This should be an
                          instance of a message in the message directory that
                          that starts with 'Out'.
          msg_handler:    Message handler instance to use when replies to the
                          message are received.  Any message received after we
                          write out the msg are passed to this handler until
                          the handler returns the message.FINISHED flags.
          high_priority:  (bool)False to add the message at the end of the
                          queue.  True to insert this message at the start of
                          the queue.
        """
        if not high_priority:
            self._write_queue.append((msg, msg_handler))
        else:
            self._write_queue.insert(0, (msg, msg_handler))

        # If there is an existing msg that we're processing replies
        # for then delay sending this until we're done.
        if not self._write_handler:
            self._send_next_msg()

    #-----------------------------------------------------------------------
    def _poll(self, t):
        """Periodic polling function.

        The network stack calls this periodically.  If we have message
        handler, we'll use this to check for a time out if the correct
        set of replies hasn't been received yet.

        Args:
           t:   (float) Current Unix clock time tag.
        """
        if not self._write_handler:
            return

        # Ask the write handler if it's past the time out in which
        # case we'll mark this message as finished and move on.
        if self._write_handler.is_expired(self, t):
            LOG.warning("Last message timed out")
            self._write_finished()

    #-----------------------------------------------------------------------
    def _data_read(self, link, data):
        """PLM modem data read callback.

        This is called by the network loop when data is read from the
        modem.  We'll add it to our read buffer and try to find any
        insteon messages that are in it.

        Args:
          link:    network.Link The serial connection that read the data.
          data:    bytes: The data that was read.
        """
        # Append the read data to the inbound message buffer.
        self._buf.extend(data)

        # Keep processing until there are no more messages to handle.
        # There must be at least 2 bytes so we can read the message
        # type code.
        while len(self._buf) > 1:
            #LOG.debug("Searching message (len %d): %s... ",
            #               len(self._buf), tohex(self._buf,10))

            # Find a message start token.  Note that this token could
            # also appear in the middle of a message so we can't be
            # totally sure it's a message until we try to parse it.
            # If there is no starting token - we're probably reading
            # at the start in the middle of a message so just clear it
            # and wait until we get a start token.
            start = self._buf.find(0x02)
            if start == -1:
                LOG.debug("No 0x02 starting byte found - clearing")
                self._buf = bytearray()
                break

            # Move the buffer to the start token.  Make sure we still
            # have at lesat 2 bytes or wait for more to arrive.
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

            # See if we have enough bytes to read the message.  If
            # not, wait until more data is read.
            msg_size = msg_class.msg_size(self._buf)
            if len(self._buf) < msg_size:
                break

            # Read the message and move the buffer forward.
            msg = msg_class.from_bytes(self._buf)
            self._buf = self._buf[msg_size:]

            LOG.info("Read %#04x: %s", msg_type, msg)

            # And try to process the message using the handlers.
            self._process_msg(msg)

    #-----------------------------------------------------------------------
    def _process_msg(self, msg):
        """Process a read message by passing it to the handlers.

        If we wrote out a message, we'll try and use the message
        handler for that message first.  If not or if that handler
        doesn't understand the message, we'll pass it to the read
        handlers for processing.

        Args:
          msg:   Insteon message object to process.
        """
        # If we have a write handler, then most likely the inbound
        # message is a reply to the write so see if it can handle the
        # message.  If the status is FINISHED, then the handler has
        # seen all the messages it expects. If it's CONTINUE, it
        # processed the message but expects more.  If it's UNKNOWN,
        # the handler ignored that message.
        if self._write_handler:
            LOG.debug("Passing msg to write handler")
            status = self._write_handler.msg_received(self, msg)

            # Handler is finished.  Send the next outgoing message
            # if one is waiting.
            if status == Msg.FINISHED:
                LOG.debug("Write handler finished")
                self._write_finished()
                return

            # If this message was understood by the write handler,
            # don't look in the read handlers and update the write
            # handlers time out into the future.
            elif status == Msg.CONTINUE:
                self._write_handler.update_expire_time()
                return

        # No write handler or the message didn't match what the
        # handler expects to see.  Try the regular read handler to see
        # if they understand the message.
        for handler in self._read_handlers:
            status = handler.msg_received(self, msg)

            # If the message was understood by this handler return.
            # This limits us to one handler per message but that's
            # probably ok.
            if status != Msg.UNKNOWN:
                return

        # No handler was found for the message.  Shift pass the ID
        # code and look for more messages.  This might be better
        # by having a lookup by msg ID->msg size and use that to
        # skip the whole message.
        LOG.warning("No read handler found for message type %#04x: %s",
                    msg.msg_code, msg)

    #-----------------------------------------------------------------------
    def _write_finished(self):
        """Message written finished.

        This is called when the write message handler returns
        message.FINISHED which means all the expected replies have
        been read.  The write handler is cleared and the next message
        in the queue is written.
        """
        assert self._write_handler

        self._write_handler = None
        if self._write_queue:
            self._send_next_msg()

    #-----------------------------------------------------------------------
    def _msg_written(self, link, data):
        """Message written callback.

        This is called by the network link when the message packet has
        been written to the modem.
        """
        # Currently we don't need to do anything.
        pass

    #-----------------------------------------------------------------------
    def _send_next_msg(self):
        """Send the next message in the write queue.

        This pops off the first message in the queue and sets it into
        the write_data field for later processing of replies.
        """
        # Get the next output message and handler from the write
        # queue.
        msg, handler = self._write_queue.pop(0)
        bytes = msg.to_bytes()

        LOG.info("Write to modem: %s", msg)
        from . import util
        LOG.debug("Write to modem: %s", util.to_hex(bytes))

        # Write the message to the PLM modem.
        self.link.write(bytes)

        # Tell the msg data that we've sent the message to update the
        # current time out time.
        handler.update_expire_time()

        # Save the handler to have priority processing any inbound
        # messages.
        self._write_handler = handler

    #-----------------------------------------------------------------------
