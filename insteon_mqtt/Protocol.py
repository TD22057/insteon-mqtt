#===========================================================================
#
# Insteon modem
#
#===========================================================================
import logging
from .Address import Address
from . import message as Msg
from . import util

LOG = logging.getLogger(__name__)


class Protocol:
    """Insteon PLM protocol processing class.

    This class processes the byte stream that is being read from and
    written to the Insteon PLM modem.  
    """
    def __init__(self, link):
        self.link = link

        link.signal_read.connect(self._data_read)
        link.signal_wrote.connect(self._msg_written)

        # Inbound message buffer.
        self._buf = bytearray()

        # Tuple of (msg,handler) which is the queue of messages to
        # send.  Each message comes with a handler to process
        # responses.  We have to wait until the handler says that it's
        # done receiving replies until we can send the next message.
        # If we write to the modem before that, it basically cancels
        # the previous action.  When a message is written, it's
        # handler gets set into _write_handler until that handler says
        # that's received all the expected replies (or times out).  At
        # that point we'll write the next message in the queue.
        self._write_queue = []
        self._write_handler = None

        # Set of possible message handlers to use.  These are handlers
        # that handle any message besides the replies expected by the
        # write handler.
        self._read_handlers = []

    #-----------------------------------------------------------------------
    def add_handler(self, handler):
        self._read_handlers.append(handler)
        
    #-----------------------------------------------------------------------
    def remove_handler(self, handler):
        self._read_handlers.pop(handler, None)
        
    #-----------------------------------------------------------------------
    def load_config(self, config):
        self.link.load_config(config)

    #-----------------------------------------------------------------------
    def send(self, msg, msg_handler):
        self._write_queue.append((msg, msg_handler))

        # If there is an existing msg that we're processing replies
        # for then delay sending this until we're done.
        if not self._write_handler:
            self._send_next_msg()

    #-----------------------------------------------------------------------
    def _data_read(self, link, data):
        # Append the read data to the inbound message buffer.
        self._buf.extend(data)

        # Use cases:
        #
        # 1) Replies from commands we send to the modem.  For a
        #    std msg (8 bytes), we'll get a echo reply w/ ACK/NAK (9
        #    bytes).  If this fails, we'll get a 2 byte NAK.  After
        #    the ACK, we'll probably also get further messages in.  If
        #    we don't wait for these and continue writing messages,
        #    the modem won't send them (but will ACK them).  So once
        #    we send a message, we need to know what the expected
        #    reply is going to be and wait for that.
        #
        # 2) inbound msg from modem when a device triggers and sends a
        #    message to the modem.  This will be an 11 byte std msg.
        #
        # 3) Device database reading.  Reading remote db's involves
        #    sending one command, getting an ACK, then reading a series
        #    of messages (1 per db entry) until we get a final message
        #    which ends the sequence.

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

            # Messages are 0x02 TYPE so find map the type code to the
            # message class we need to use to read it.
            msg_type = self._buf[1]
            msg_class = Msg.types.get(msg_type, None)
            if not msg_class:
                LOG.info("Skipping unknown message type %#04x", msg_type)
                self._buf = self._buf[2:]
                continue

            # Try and read the message - if we get back an int, it's
            # the number of bytes we need to have before proceeding.
            # Future enhancement is to retain that and skip directly
            # here when we have that many bytes.  Current system works
            # fine but is inefficient since it tries to read over and
            # over again.
            msg = msg_class.from_bytes(self._buf)
            if isinstance(msg, int):
                break

            # We read a message type.  Move the buffer forward to the
            # end of the message.
            LOG.info("Read %#04x: %s", msg_type, msg)
            self._buf = self._buf[msg.msg_size:]

            # And process the message using the handlers.
            self._process_msg(msg)

    #-----------------------------------------------------------------------
    def _process_msg(self, msg):
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
                self._write_handler = None
                if self._write_queue:
                    self._send_next_msg()

            # If this message was understood by the write handler,
            # don't look in the read handlers.
            if status != Msg.UNKNOWN:
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
        LOG.warning("No read handler found for message type %#04x", msg.code)

    #-----------------------------------------------------------------------
    def _msg_written(self, link, data):
        #LOG.info("Message sent: %s",data)
        pass

    #-----------------------------------------------------------------------
    def _send_next_msg(self):
        # Get the next message and handler from the write queue.
        msg, msg_handler = self._write_queue.pop(0)

        LOG.info("Write to PLM: %s", msg)

        # Write the message to the PLM modem.
        self.link.write(msg.to_bytes())

        # Save the handler to have priority processing any inbound
        # messages.
        self._write_handler = msg_handler

    #-----------------------------------------------------------------------
    

#===========================================================================
