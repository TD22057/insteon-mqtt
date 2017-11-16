#===========================================================================
#
# Base message class
#
#===========================================================================


class Base:
    """Base message class

    This sets the basic message API that all the classes support.  If
    the message is fixed length, set fixed_msg_size, otherwise
    implement msg_size().
    """
    msg_code = None  # set to the message ID byte.
    fixed_msg_size = None  # set if the message is fixed length.

    #-----------------------------------------------------------------------
    @staticmethod
    def from_bytes(raw):
        """Read the message from a byte stream.

        This should only be called if raw[1] == msg_code and len(raw)
        >= msg_size().

        Args:
           raw   (bytes): The current byte stream to read from.

        Returns:
           Returns the constructed message object.
        """
        raise NotImplementedError("from_bytes() not implemented")

    #-----------------------------------------------------------------------
    def msg_size(self, raw):
        """Return the message size in bytes.

        Standard and Extended messages depend on the message flags
        inside the message so some types will need to parse part of
        the byte array to figure out the total size.

        Args:
           raw   (bytes): The current byte stream to read from.

        Returns:
           Returns the constructed message object.

        """
        if self.fixed_msg_size:
            return self.fixed_msg_size
        else:
            raise NotImplementedError("%s.msg_size() not implemented" %
                                      self.__class__)

    #-----------------------------------------------------------------------
    def to_bytes(self):
        """Convert the message to a byte array.

        Returns:
           (bytes) Returns the message as bytes.
        """
        raise NotImplementedError("%s.to_bytes() not implemented" %
                                  self.__class__)

    #-----------------------------------------------------------------------

#===========================================================================
