#===========================================================================
#
# Base message class
#
#===========================================================================


class Base:
    """Base message class

    This sets the basic message API that all the classes support.  If the
    message is fixed length, set fixed_msg_size, otherwise implement
    msg_size().
    """
    msg_code = None  # set to the message ID byte.

    # Read message size (including ack/nak byte).  Derived types should set
    # this if the message has fixed size otherwise implement msg_size().
    fixed_msg_size = None

    #-----------------------------------------------------------------------
    @classmethod
    def from_bytes(cls, raw):
        """Read the message from a byte stream.

        This should only be called if raw[1] == msg_code and len(raw) >=
        msg_size().

        Args:
          raw (bytes):  The current byte stream to read from.

        Returns:
          Returns the constructed message object.
        """
        raise NotImplementedError("%s.from_bytes() not implemented" % cls)

    #-----------------------------------------------------------------------
    @classmethod
    def msg_size(cls, raw):
        """Return the read message size in bytes.

        This is the input message size to read when we see msg_code in the
        byte stream.

        Standard and Extended messages depend on the message flags inside the
        message so some types will need to parse part of the byte array to
        figure out the total size.

        Args:
          raw (bytes):  The current byte stream to read from.

        Returns:
          int:  Returns the number of bytes needed to construct the message.
        """
        if cls.fixed_msg_size:
            return cls.fixed_msg_size
        else:
            raise NotImplementedError("%s.msg_size() not implemented" % cls)

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Convert the message to a byte array.

        Returns:
          bytes:  Returns the message as bytes.
        """
        # NOTE: This is only needed for output messages.
        raise NotImplementedError("%s.to_bytes() not implemented" %
                                  self.__class__)

    #-----------------------------------------------------------------------

#===========================================================================
