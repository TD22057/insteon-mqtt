#===========================================================================
#
# Network and serial link management
#
#===========================================================================
from .. import Signal


class Link:
    """TODO: doc
    """

    def __init__(self):
        """TODO: doc
        """
        # Sent when the link is going down.
        # signature: (Link link)
        self.signal_closing = Signal.Signal()

        # Sent when the link changes state on whether or not it has
        # bytes that need to be written to the link.
        # signature: (Link link, bool write_active)
        self.signal_needs_write = Signal.Signal()

        # The manager will emit this after the connection has been
        # established and everything is ready.  Links should usually
        # not emit this directly.
        # signature: (Link link, bool connected)
        self.signal_connected = Signal.Signal()

    #-----------------------------------------------------------------------
    def retry_connect_dt(self):
        """TODO: doc
        """
        return None

    #-----------------------------------------------------------------------
    def connect(self):
        """TODO: doc
        """
        return False

    #-----------------------------------------------------------------------
    def fileno(self):
        """TODO: doc
        """
        raise NotImplementedError("{} needs fileno() method".format(
                                  self.__class__))

    #-----------------------------------------------------------------------
    def poll(self, t):
        """TODO: doc
        """
        pass

    #-----------------------------------------------------------------------
    def read_from_link(self):
        """TODO: doc
        """
        raise NotImplementedError("{} needs read_from_link() method".format(
                                  self.__class__))

    #-----------------------------------------------------------------------
    def write_to_link(self):
        """TODO: doc
        """
        raise NotImplementedError("{} needs write_to_link() method".format(
                                  self.__class__))

    #-----------------------------------------------------------------------
    def close(self):
        """TODO: doc
        """
        raise NotImplementedError("{} needs close() method".format(
                                  self.__class__))

    #-----------------------------------------------------------------------
