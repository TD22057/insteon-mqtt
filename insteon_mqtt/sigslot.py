#===========================================================================
#
# Signal/slot pattern signal object for weak coupling.
#
#===========================================================================
import inspect
import weakref


class Signal:
    """Signal pattern class.

    A signal is an object that can be connected to an arbitrary number
    of slots which are functions or instance methods.  When the signal
    is emitted (by calling emit()), each slot is called with any
    arguments passed to the emit method.
    """
    #-----------------------------------------------------------------------
    def __init__(self):
        """Constructor
        """
        # Weak references to functions or methods
        self.slots = []

    #-----------------------------------------------------------------------
    def emit(self, *args, **kwargs):
        """Emit the signal.
        All of the connected slots will be called with the input args
        and kwargs.
        """
        # Loop in reverse order over the slots.  That way we can
        # delete any weak references that no longer exist and support
        # a slot that calls disconnect on itself in the middle of the
        # loop.
        for i, wr_slot in enumerate(reversed(self.slots)):
            slot = wr_slot()
            if slot is not None:
                slot(*args, **kwargs)
            else:
                del self.slots[i]

    #-----------------------------------------------------------------------
    def connect(self, slot):
        """Connect a slot to the signal.

        If the input slot is already connected, nothing is done.

        = INPUTS
        - slot   Instance method or function to connect.
        """
        if inspect.ismethod(slot):
            wr_slot = weakref.WeakMethod(slot)
        else:
            wr_slot = weakref.ref(slot)

        # If the index method throws, the slot doesn't exist yet.
        try:
            self.slots.index(wr_slot)
        except ValueError:
            # Insert it at the beginning so that when we call the
            # slots in reverse order, they will be called in the order
            # inserted.
            self.slots.insert(0, wr_slot)

    #-----------------------------------------------------------------------
    def disconnect(self, slot):
        """Disconnect a slot from the signal.

        If the input slot is not connected, nothing is done.

        = INPUTS
        - slot   Instance method or function to disconnect.
        """
        if inspect.ismethod(slot):
            wr_slot = weakref.WeakMethod(slot)
        else:
            wr_slot = weakref.ref(slot)

        try:
            self.slots.remove(wr_slot)
        except ValueError:
            pass

    #-----------------------------------------------------------------------
    def clear(self):
        """Clear all the attached slots from the signal.
        """
        self.slots = []

    #-----------------------------------------------------------------------
