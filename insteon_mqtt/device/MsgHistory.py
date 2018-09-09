#===========================================================================
#
# Message history class
#
#===========================================================================
import math
from .. import log

LOG = log.get_logger()


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
        LOG.debug("Received %s hops, total %d for %d entries", num_hops,
                  self._hopSum, len(self._hops))

        # If we've gone over the window size, remove the oldest value.
        if len(self._hops) > self.WINDOW_LEN:
            old_num = self._hops.pop(0)
            self._hopSum -= old_num

    #-----------------------------------------------------------------------
    def avg_hops(self):
        """Compute the number of optimal number hops for an outbound message.

        Returns:
          (int) Returns the number of hops to use in the range [0,3].
        """
        if not self._hops:
            return 3

        # Compute the average # of hops in the buffer.
        avg_hops = float(self._hopSum) / len(self._hops)

        # Round up and use at least 1 hop
        num_hops = max(0, int(math.ceil(avg_hops)))
        num_hops = min(3, num_hops)
        LOG.debug("Average hops %03.1f, using %d", avg_hops, num_hops)
        return num_hops

    #-----------------------------------------------------------------------
