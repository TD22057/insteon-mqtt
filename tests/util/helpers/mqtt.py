#===========================================================================
#
# Common code test helpers.  These are common classes used by multiple tests.
#
#===========================================================================
import insteon_mqtt as IM

#===========================================================================
class MockModem:
    """Mock insteon_mqtt/mqtt/Modem class
    """
    signal_new_device = IM.Signal()


#===========================================================================
