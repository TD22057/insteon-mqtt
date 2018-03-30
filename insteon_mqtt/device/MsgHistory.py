#===========================================================================
#
# Message history class
#
#===========================================================================
import math


class MsgHistory:
    """Message history tracking.

    This class is used to track the history of messages received by a device.
    It's primarily used to compute the most efficient hop value to use for
    outbound messages by tracking the hop values of the messages that are
    received from the device.
    """
    # Number of messages to use in the averaging.
    WINDOW_LEN = 10

    #-----------------------------------------------------------------------
    def __init__(self):
        """Constructor
        """
        # List of the number of messages hops that were taken for up to
        # NUM_AVG of the last messages.
        self._hops = []

        # Sum of the number of hops in self._hops.
        self._hopSum = 0

    #-----------------------------------------------------------------------
    def add(self, msg):
        """Add a received message to the history.

        Args:
           msg:    (Msg.Base) The received message.
        """
        num_hops = msg.flags.max_hops - msg.flags.hops_left
        self._hops.append(num_hops)
        self._hopSum += num_hops

        # If we've gone over the window size, remove the oldest value.
        if len(self._hops) > self.WINDOW_LEN:
            old_num = self._hops.pop(0)
            self._hopSum -= old_num

    #-----------------------------------------------------------------------
    def hops(self):
        """Compute the number of optimal number hops for an outbound message.

        Returns:
          (int) Returns the number of hops to use in the range [1,3].
        """
        if not self._hops:
            return 3

        # Compute the average # of hops and round up.
        average = int(math.ceil(self._hopSum / float(len(self._hops))))

        return max(average, 3)

    #-----------------------------------------------------------------------
