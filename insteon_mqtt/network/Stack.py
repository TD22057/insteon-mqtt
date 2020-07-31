#===========================================================================
#
# Stack class definition.
#
#===========================================================================
import tempfile
from ..Signal import Signal
from .. import log

LOG = log.get_logger(__name__)


class Stack:
    """A Fake Network Interface for Queueing and 'Asynchronously' Running
    Functional Calls

    This class appears as though it is a read/write interface that is handled
    my the network manager.  But in reality it is just a wrapper for inserting
    function calls into the network loop.  This allows long functional calls
    to be broken up into multiple sub calls that can be called on seperate
    iterations of the main loop.

    This isn't true asynchronous functionality, but it prevents the main loop
    from halting for too long.

    At the moment, and as best I can currently envision, this class is only
    necessary for the import_scenes functionality.  I can't imagine any other
    process that would require such complex and long running functions.
    """

    def __init__(self):
        """Constructor.  Mostly just defines some attributes that are expected
        but un-needed.
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

        # Generate a fileno using a temp file.  We could just pass 0, which
        # seems to work, but not sure if this could cause a subtle bug. It
        # might be better to have this be an actual file
        self.tempfile = tempfile.TemporaryFile()

        # The list of groups of functions to call.  Each item should be a
        # StackGroup
        self.groups = []

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
        return True

    #-----------------------------------------------------------------------
    def fileno(self):
        """Return the file descriptor to watch for this link.

        Returns:
          int:  Returns the descriptor (obj.fileno() usually) to monitor.
        """
        return self.tempfile

    #-----------------------------------------------------------------------
    def poll(self, t):
        """Periodic poll callback.

        The manager will call this at recurring intervals in case the link
        needs to do some periodic manual processing.

        This is where we inject the function calls.  One call is made for each
        instance of this call.  Essentially we make one function call per loop.
        Then if other read or writing of other network items needs to take
        place they will be called before the next function call is made.

        If there is an exception raised during the function call, if error_stop
        is True, the entire group of function calls is cancelled.

        Args:
           t (float):  Current Unix clock time tag.
        """
        if len(self.groups) > 0:
            group = self.groups[0]
            entry = group.get_next()
            if entry is None:
                # If no more function entries, then delete this group
                self.groups.pop(0)
            else:
                try:
                    entry[0](*entry[1], **entry[2])
                except:
                    if group.error_stop:
                        LOG.error("Error in executing stack function, "
                                  "stopping all remaining functions in the "
                                  "group")
                        self.groups.pop(0)
                    else:
                        LOG.error("Error in executing stack function, "
                                  "continuing on to next function.")

    #-----------------------------------------------------------------------
    def new(self, error_stop=True):
        """Initialize and create a new group of functional calls`

        Args:
          error_stop (bool): If True, if an exception is raised during any of
                             the function calls, the remainder of the calls
                             are skipped.

        Returns:
          StackGroup"""
        new_stack = StackGroup(error_stop)
        self.groups.append(new_stack)
        return new_stack

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


class StackGroup:
    """A Simple Class for Grouping Functional Calls

    Essentially just a list of functional calls to make, with an attribute that
    defines what happens if an exception is raised during a call.
    """

    def __init__(self, error_stop=True):
        """Constructor

        Args:
          error_stop (bool): If True, will skip the remaining funciton calls
                             if any function call raises an exception.
        """
        self.error_stop = error_stop
        self.funcs = []

    def add(self, func, *args, **kwargs):
        """ Appends a function call to the list of calls to make
        """
        self.funcs.append([func, args, kwargs])

    def get_next(self):
        """ Pops the next function call off of the start of the list.

        Returns:
          The next functional call as a list of len 3.  Otherwise None if there
          are no more calls
        """
        if len(self.funcs) > 0:
            return self.funcs.pop(0)
        else:
            return None
