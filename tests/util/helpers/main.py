#===========================================================================
#
# Common code test helpers.  These are common classes used by multiple tests.
#
#===========================================================================
import insteon_mqtt as IM
from .Data import Data

#===========================================================================
class MockModem:
    """Mock insteon_mqtt/Modem class
    """
    # Use the 'tmpdir' fixture and pass that to this constructor.
    def __init__(self, save_path):
        self.name = "modem"
        self.addr = IM.Address(0x20, 0x30, 0x40)
        self.save_path = str(save_path)
        self.scenes = []
        self.devices = {}
        self.device_names = {}

    def add(self, device):
        self.devices[device.addr.id] = device
        if device.name:
            self.device_names[device.name] = device

    def find(self, addr):
        device = self.devices.get(addr.id, None)
        return device

    def remove(self, device):
        self.devices.pop(device.addr.id, None)
        if device.name:
            self.device_names.pop(device.name, None)

    def scene(self, is_on, group, num_retry=3, on_done=None, reason=""):
        self.scenes.append((is_on, group, reason))


#===========================================================================
class MockProtocol:
    """Mock insteon_mqtt/Protocol class
    """
    def __init__(self):
        self.signal_received = IM.Signal()
        self.signal_msg_finished = IM.Signal()
        self.sent = []

    def clear(self):
        self.sent = []

    def send(self, msg, handler, priority=None, after=None):
        self.sent.append(Data(msg=msg, handler=handler))

    def add_handler(self, handler):
        pass

    def set_wait_time(self, seconds):
        pass


#===========================================================================
