#===========================================================================
#
# Network and serial link management
#
#===========================================================================
from .. import Signal


class Link:
    #-----------------------------------------------------------------------
    def __init__(self):
        # Sent when the link is going down.
        # signature: (Link link)
        self.signal_closing = Signal.Signal()

        # Sent when the link changes state on whether or not it has
        # bytes that need to be written to the link.
        # signature: (Link link, bool write_active)
        self.signal_needs_write = Signal.Signal()

    #-----------------------------------------------------------------------
    def retry_connect_dt(self):
        return None

    #-----------------------------------------------------------------------
    def connect(self):
        return False

    #-----------------------------------------------------------------------
    def fileno(self):
        raise NotImplementedError("{} needs fileno() method".format(
                                  self.__class__))

    #-----------------------------------------------------------------------
    def read_from_link(self):
        raise NotImplementedError("{} needs read_from_link() method".format(
                                  self.__class__))

    #-----------------------------------------------------------------------
    def write_to_link(self):
        raise NotImplementedError("{} needs write_to_link() method".format(
                                  self.__class__))

    #-----------------------------------------------------------------------
    def close(self):
        raise NotImplementedError("{} needs close() method".format(
                                  self.__class__))

    #-----------------------------------------------------------------------
