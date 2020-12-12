#===========================================================================
#
# TimedCall class definition.
#
#===========================================================================
from ..Signal import Signal
from .. import log

LOG = log.get_logger(__name__)


class TimedCall:
    """A Fake Network Interface for Queueing and 'Asynchronously' Running
    Functional Calls at Specific Times

    This is a polling only network "link".  Unlike regular links that do read
    and write operations when they report they are ready, this class is
    designed to only be polled during the event loop.

    This is like a network link for reading and writing but  that is handled
    by the network manager.  But in reality it is just a wrapper for inserting
    function calls into the network loop near specific time.  This allows
    function calls to be scheduled to run at specific times.

    This isn't true asynchronous functionality, there is no gaurantee that the
    call will run at the time specified, only that it will run at some point
    after the specified time.  In general, this lag is minimal, likely tens of
    milliseconds.  However, as a result, this class should not be used for
    time critical functions.

    This class was originally created to handle the reverting of the relay
    state for momentary switching on the IOLinc.  Other time based objects
    may also benefit from this.
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

        # The list of functions to call.  Each item should be a
        # CallObject
        self.calls = []

    #-----------------------------------------------------------------------
    def poll(self, t):
        """Periodic poll callback.

        The manager will call this at recurring intervals in case the link
        needs to do some periodic manual processing.

        This is where we inject the function calls.  The main loop calls this
        once per loop.  This checks to see if the time associated with any of
        the CallObjects has elapsed.  If it has, call the function.

        Only a single call is performed each loop.  Currently, there is no
        reason to think that multiple calls would be necessary.

        Args:
           t (float):  Current Unix clock time tag.
        """
        if len(self.calls) > 0:
            if self.calls[0].time < t:
                entry = self.calls.pop(0)
                try:
                    entry.func(*entry.args, **entry.kwargs)
                except:
                    LOG.error("Error in executing TimedCall function")

    #-----------------------------------------------------------------------
    def add(self, time, func, *args, **kwargs):
        """Adds a call to the calls list and sorts the list

        Args:
          time (float):  The Unix clock time tag at which the call should run
          func (function): The function to run
          ars & kwargs: Passed to the function when run
        Returns:
          The created (CallObject)
         """
        new_call = CallObject(time, func, *args, **kwargs)
        self.calls.append(new_call)
        self.calls.sort(key=lambda call: call.time)
        return new_call

    #-----------------------------------------------------------------------
    def remove(self, call):
        """Removes a call from the calls list

        Args:
          call (CallObject):  The CallObject to delete, from add()
        Returns:
          True if a call was removed, False otherwise
        """
        ret = False
        if call in self.calls:
            self.calls.remove(call)
            ret = True
        return ret

    #-----------------------------------------------------------------------
    def close(self):
        """Close the link.

        The link must call self.signal_closing.emit() after closing.
        """
        self.signal_closing.emit()

    #-----------------------------------------------------------------------


#===========================================================================
class CallObject:
    """A Simple Class for Associating a Time with a Call
    """

    def __init__(self, time, func, *args, **kwargs):
        """Constructor

        Args:
          error_stop (bool): If True, will skip the remaining funciton calls
                             if any function call raises an exception.
        """
        self.time = time
        self.func = func
        self.args = args
        self.kwargs = kwargs
