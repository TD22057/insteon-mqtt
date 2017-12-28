#===========================================================================
#
# Command sequence class
#
#===========================================================================
from . import log
from . import util

LOG = log.get_logger()


class CommandSeq:
    """Series of commands to run sequentially.

    This class stores a series of commands that run sequentially (using
    on_done callbacks to trigger the next command).  If any command fails, it
    stops the sequence.

    Ideally there is a better way to this but I couldn't come up with any.
    Since each call is via callback, the stack grows longer and longer so
    this shouldn't be used for 100+ calls but for the small number of calls
    this library needs, it works ok.

    This type of class is needed because we need to send series of commands.
    And each one needs to return so that the event loop can process the
    network activity to actually run the command.  In the future, this is
    probably a good case for switching to asyncio type processing.
    """
    #-----------------------------------------------------------------------
    def __init__(self, msg=None, on_done=None):
        """Constructor

        Args:
          msg:      Message to pass to on_done if the sequence works.
          on_done:  The callback to run when complete.  This will be run
                    when there is an error or when all the commands finish.
        """
        self._on_done = util.make_callback(on_done)
        self.msg = msg
        self.calls = []
        self.total = 0

    #-----------------------------------------------------------------------
    def add(self, func, *args, **kwargs):
        """Add a call to the sequence.

        Args:
          func:     The function or method to call.  Must take an on_done
                    callback argument.
          args:     Arguments to pass to the function.
          kwargs:   Keyword arguments to pass to the function.
        """
        self.calls.append((func, args, kwargs))
        self.total += 1

    #-----------------------------------------------------------------------
    def run(self):
        """Run the sequence.

        Depending on the functions in the sequence, this generally returns
        right away.  When the current command finishes, the on_done callback
        to that command triggers the next call.
        """
        self.on_done(True, None, None)

    #-----------------------------------------------------------------------
    def on_done(self, success, msg, data):
        """TODO: doc
        """
        # Last function failed with an error.
        if not success:
            self._on_done(success, msg, data)

        # No more calls - success.
        elif not self.calls:
            self._on_done(success, self.msg, data)

        # Otherwise run the next command.
        else:
            LOG.debug("Running command %d of %d", self.total + 1 -
                      len(self.calls), self.total)

            func, args, kwargs = self.calls.pop(0)
            func(*args, on_done=self.on_done, **kwargs)

    #-----------------------------------------------------------------------
