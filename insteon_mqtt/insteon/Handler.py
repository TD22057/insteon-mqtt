#===========================================================================
#
# Insteon modem
#
#===========================================================================
from .Address import Address
from . import msg as Msg
import logging
import io
import binascii

class Handler:
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
        self._read_handlers = {}
        #    Msg.StandardHandler.code : Msr.StandardHandler(),
        #    }

        self.log = logging.getLogger(__name__)

    #-----------------------------------------------------------------------
    def load_config(self, config):
        self.link.load_config(config)

    #-----------------------------------------------------------------------
    def send(self, msg, msgHandler):
        self._write_queue.append((msg, msgHandler))

        # If there is an existing msg in the write queue, we're either
        # waiting to write it or waiting for a reply.  So only write
        # this to the modem if it's the only message we have left.
        if len(self._write_queue) == 1:
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
        # sending one command, getting an ACK, then reading a series
        # of messages (1 per db entry) until we get a final message
        # which ends the sequence.

        # Keep processing until there are no more messages to handle.
        # There must be at least 2 bytes so we can read the message
        # type code.
        while len(self._buf) > 1:
            #self.log.debug("Searching message (len %d): %s... ",
            #               len(self._buf), tohex(self._buf,10))
            
            # Find a message start token.  Note that this token could
            # also appear in the middle of a message so we can't be
            # totally sure it's a message until we try to parse it.
            # If there is no starting token - we're probably reading
            # at the start in the middle of a message so just clear it
            # and wait until we get a start token.
            start = self._buf.find(0x02)
            if start == -1:
                self.log.debug("No 0x02 starting byte found - clearing")
                self.clear()
                break

            # Move the buffer to the start token.
            if start != 0:
                self.log.debug("0x02 found at byte %d - shifting", start)
                self._buf = self._buf[start:]
                if len(self._buf) < 2:
                    continue

            msg_type = self._buf[1]
            msg_class = Msg.types.get(msg_type, None)
            if not msg_class:
                self.log.info("Skipping unknown message type %#04x", msg_type)
                self._buf = self._buf[2:]
                continue

            # Try and read the message - if this fails, we don't have
            # enough bytes.
            msg = msg_class.read(self._buf)
            if isinstance(msg, int):
                break

            self.log.info("Read %#04x: %s", msg_type, msg)
            self._buf = self._buf[msg.msg_size:]

            self.process_msg(msg)

    #-----------------------------------------------------------------------
    def process_msg(self, msg):
        # If we have a write handler, then most likely the inbound
        # message is a reply to the write so see if it can handle
        # the message.
        if self._write_handler:
            self.log.debug("Passing msg to write handler")
            status = self._write_handler.handle(msg)
            # status:
            # CONTINUE: message handled but waiting for more messages
            # FINISHED: all expected replies have arrived

            # Handler is finished.  Send the next outgoing message
            # if one is waiting.
            if status == Msg.FINISHED:
                self.log.debug("Write handler %s finished",
                               self._write_handler.name)
                self._write_handler = None
                if self._write_queue:
                    self._send_next_msg()

            # If this message was understood by the write handler,
            # don't look in the read handlers.
            if status != Msg.UNKNOWN:
                return

        # No write handler or the message didn't match what the
        # handler expects to see.  Try the regular read handler to
        # see if they understand the message.
        handler = self._read_handlers.get(msg.code, None)
        if handler:
            status = handler.handle(msg)
            if status == Msg.FINISHED:
                self.log.debug("Read handler %s finished", handler.name)

        # No handler was found for the message.  Shift pass the ID
        # code and look for more messages.  This might be better
        # by having a lookup by msg ID->msg size and use that to
        # skip the whole message.
        else:
            self.log.warning("No read handler found for message type %#04x",
                             msg.code)

    #-----------------------------------------------------------------------
    def _msg_written(self, link, data):
        self.log.info("MSG sent: %s",data)

    #-----------------------------------------------------------------------
    def _send_next_msg(self):
        msg, handler = self._write_queue.pop(0)
        self.link.write(msg.bytes())
        self._write_handler = handler

    #-----------------------------------------------------------------------
    
#===========================================================================
def tohex(data, num=None):
    if num:
        data = data[:num]

    s = binascii.hexlify(data).decode()
    o = io.StringIO()
    for i in range( 0, len( s ), 2 ):
        o.write( s[i] )
        o.write( s[i+1] )
        o.write( ' ' )
    return o.getvalue()

#===========================================================================
