#===========================================================================
#
# Network Link base class definition.
#
#===========================================================================
from ..Signal import Signal


class Link:
    """Network link (file, socket, etc) to monitor for reading and writing.

    A Link represents a connection to a device that needs to be watched for
    reading and writing events.  It works with a poll.Manager event loop to
    allow efficient reading and writing of network (or network like) based
    connections.

    The link reports to the manager via signals when there is data to write
    (or not) and when the link is closing.  The manager will call
    read_from_link() and write_to_link() when the link can actually perform
    those actions.
    """

    def __init__(self):
        """Constructor.
        """
        # Sent when the link is going down.  signature: (Link link)
        self.signal_closing = Signal()

        # Sent when the link changes state on whether or not it has bytes
        # that need to be written to the link.  signature: (Link link, bool
        # write_active)
        self.signal_needs_write = Signal()

        # The manager will emit this after the connection has been
        # established and everything is ready.  Links should usually not emit
        # this directly.  signature: (Link link, bool connected)
        self.signal_connected = Signal()

    #-----------------------------------------------------------------------
    def retry_connect_dt(self):
        """Return a positive integer (seconds) if the link should reconnect.

        If this returns None, the link will not be reconnected if it closes.
        Otherwise this is the retry interval in seconds to try and reconnect
        the link by calling connect().
        """
        return None

    #-----------------------------------------------------------------------
    def connect(self):
        """Connect the link to the device.

        This should connect to the socket, serial port, file, etc.

        Returns:
          bool:  Returns True if the connection was successful or False it
          it failed.
        """
        return False

    #-----------------------------------------------------------------------
    def fileno(self):
        """Return the file descriptor to watch for this link.

        Returns:
          int:  Returns the descriptor (obj.fileno() usually) to monitor.
        """
        raise NotImplementedError("%s.fileno() not implemented" %
                                  self.__class__)

    #-----------------------------------------------------------------------
    def poll(self, t):
        """Periodic poll callback.

        The manager will call this at recurring intervals in case the link
        needs to do some periodic manual processing.

        Args:
           t (float):  Current Unix clock time tag.
        """
        pass

    #-----------------------------------------------------------------------
    def read_from_link(self):
        """Read data from the link.

        This will be called by the manager when there is data available on
        the file descriptor for reading.

        Returns:
           int:  Return -1 if the link had an error.  Or any other integer
           to indicate success.
        """
        raise NotImplementedError("%s.read_from_link() not implemented" %
                                  self.__class__)

    #-----------------------------------------------------------------------
    def write_to_link(self, t):
        """Write data from the link.

        This will be called by the manager when the file descriptor can be
        written to.  It will only be called after the link as emitted the
        signal_needs_write(True).  Once all the data has been written, the
        link should call self.signal_needs_write.emit(False).

        Args:
           t (float):  The current time (time.time).
        """
        raise NotImplementedError("%s.write_to_link() not implemented" %
                                  self.__class__)

    #-----------------------------------------------------------------------
    def close(self):
        """Close the link.

        The link must call self.signal_closing.emit() after closing.
        """
        raise NotImplementedError("%s.close() not implemented" %
                                  self.__class__)

    #-----------------------------------------------------------------------
