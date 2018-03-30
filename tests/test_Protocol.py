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

    def test_duplicate(self):
        link = MockSerial()
        proto = IM.Protocol(link)

        # test standard input
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        addr = IM.Address('0a.12.33')
        msg_keep = Msg.InpStandard(addr, addr, flags, 0x11, 0x01)
        dupe = proto._is_duplicate(msg_keep)
        assert dupe == False

        # test dupe with different hops
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False, hops_left=2, 
                          max_hops=2)
        addr = IM.Address('0a.12.33')
        msg = Msg.InpStandard(addr, addr, flags, 0x11, 0x01)
        dupe = proto._is_duplicate(msg)
        assert dupe == True
        assert len(proto._inp_msg_log) == 1
        
        # not correct message type
        msg = Msg.InpUserReset()
        dupe = proto._is_duplicate(msg)
        assert dupe == False
        
        # test deleting an expired message
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        addr = IM.Address('0a.12.44')
        msg = Msg.InpStandard(addr, addr, flags, 0x11, 0x01)
        proto._inp_msg_log.append(msg)
        msg.expire_time = 1
        assert len(proto._inp_msg_log) == 2
        proto._clean_inp_msg_log()
        assert len(proto._inp_msg_log) == 1
        assert proto._inp_msg_log[0].is_duplicate(msg_keep) == True

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
