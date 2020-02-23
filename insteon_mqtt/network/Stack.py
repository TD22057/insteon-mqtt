#===========================================================================
#
# Stack class definition.
#
#===========================================================================
from ..Signal import Signal
from .. import log

LOG = log.get_logger(__name__)


class Stack:
    """A Fake Network Interface for Queueing and 'Asynchronously' Running
    Functional Calls

    This is a polling only network "link".  Unlike regular links that do read
    and write operations when they report they are ready, this class is
    designed to only be polled during the event loop.

    This is like a network link for reading and writing but  that is handled
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

        # The manager will emit this after the connection has been
        # established and everything is ready.  Links should usually not emit
        # this directly.  signature: (Link link, bool connected)
        self.signal_connected = Signal()

        # The list of groups of functions to call.  Each item should be a
        # StackGroup
        self.groups = []

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
    def close(self):
        """Close the link.

        The link must call self.signal_closing.emit() after closing.
        """
        self.signal_closing.emit()

    #-----------------------------------------------------------------------


#===========================================================================
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
