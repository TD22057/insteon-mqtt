#===========================================================================
#
# Signal/slot pattern signal object for weak coupling.
#
#===========================================================================
import inspect
import weakref


class Signal:
    """Signal pattern class.

    A signal is an object that can be connected to an arbitrary number of
    slots which are functions or instance methods.  When the signal is
    emitted (by calling emit()), each slot is called with any arguments
    passed to the emit method so care must be taken to insure that the signal
    emitter is passing the same arguments expected by the slot.

    Slots are held in weak references so if the object goes out of scope, it
    the slot will be removed.  Slots can also disconnect themselves in the
    middle of the signal being emitted.
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

        All of the connected slots will be called with the input args and
        kwargs.

        Args:
           args:  List of positional arguments to pass.
           kwargs:  Dictionary of the keyword arguments to pass.
        """
        # Loop in reverse order over the slots.  That way we can delete any
        # weak references that no longer exist and support a slot that calls
        # disconnect on itself in the middle of the loop.
        for i in reversed(range(len(self.slots))):
            slot = self.slots[i]()
            if slot is not None:
                slot(*args, **kwargs)
            else:
                del self.slots[i]

    #-----------------------------------------------------------------------
    def connect(self, slot):
        """Connect a slot to the signal.

        If the input slot is already connected, nothing is done.

        Args:
           slot:  Instance method or function to connect.
        """
        # Create a weak reference to the method or function.
        if inspect.ismethod(slot):
            wr_slot = weakref.WeakMethod(slot)
        else:
            wr_slot = weakref.ref(slot)

        # Only insert the slot if it doesn't already exist.  If the index
        # method throws, the slot doesn't exist yet. Insert it at the
        # beginning so that when we call the slots in reverse order, they
        # will be called in the order inserted.
        if wr_slot not in self.slots:
            self.slots.insert(0, wr_slot)

    #-----------------------------------------------------------------------
    def disconnect(self, slot):
        """Disconnect a slot from the signal.

        If the input slot is not connected, nothing is done.

        Args:
           slot:  Instance method or function to disconnect.
        """
        # Create a weak reference to the method or function so that we can
        # use the comparison operator on the weakref to find the slot.
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

#===========================================================================
