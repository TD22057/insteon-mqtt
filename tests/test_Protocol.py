#===========================================================================
#
# Tests for: insteont_mqtt/handler/Protocol.py
#
# pylint: disable=protected-access
#===========================================================================
import time
import insteon_mqtt as IM
import insteon_mqtt.message as Msg


class Test_Protocol:
    def test_reads(self):
        link = MockSerial()
        IM.Protocol(link)

        link.signal_read.emit(link, bytes([0x01, 0x03, 0x04]))
        link.signal_read.emit(link, bytes([0x02, 0x03, 0x04]))

    #-----------------------------------------------------------------------

    def test_duplicate(self):
        link = MockSerial()
        proto = IM.Protocol(link)

        # test standard input
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        addr = IM.Address('0a.12.33')
        msg_keep = Msg.InpStandard(addr, addr, flags, 0x11, 0x01)
        dupe = proto._is_duplicate(msg_keep)
        assert dupe is False

        # test dupe with different hops
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False, hops_left=2,
                          max_hops=2)
        addr = IM.Address('0a.12.33')
        msg = Msg.InpStandard(addr, addr, flags, 0x11, 0x01)
        dupe = proto._is_duplicate(msg)
        assert dupe is True
        assert len(proto._read_history) == 1

        # not correct message type
        msg = Msg.InpUserReset()
        dupe = proto._is_duplicate(msg)
        assert dupe is False

        # test deleting an expired message
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        addr = IM.Address('0a.12.44')
        msg = Msg.InpStandard(addr, addr, flags, 0x11, 0x01)
        proto._read_history.append(msg)
        msg.expire_time = 1
        assert len(proto._read_history) == 2
        proto._remove_expired_read(time.time())
        assert len(proto._read_history) == 1
        assert proto._read_history[0] == msg_keep

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
