#===========================================================================
#
# Tests for: insteont_mqtt/handler/Protocol.py
#
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg


class Test_Protocol:
    def test_reads(self):
        link = MockSerial()
        proto = IM.Protocol(link)

        link.signal_read.emit(link, bytes([0x01, 0x03, 0x04]))
        link.signal_read.emit(link, bytes([0x02, 0x03, 0x04]))

    #-----------------------------------------------------------------------

#===========================================================================


class MockSerial:
    def __init__(self):
        self.signal_read = IM.Signal()
        self.signal_wrote = IM.Signal()
        self.config = None

    def poll(self):
        pass

    def load_config(self, config):
        self.config = config
