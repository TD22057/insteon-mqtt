#===========================================================================
#
# Tests for: insteont_mqtt/handler/Broadcast.py
#
# pylint: disable=protected-access
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg


class Test_Broadcast:
    def test_acks(self, tmpdir):
        proto = MockProto()
        calls = []
        modem = IM.Modem(proto, IM.network.Stack(), IM.network.TimedCall())
        modem.save_path = str(tmpdir)

        addr = IM.Address('0a.12.34')
        broadcast_to_addr = IM.Address('00.00.01')
        handler = IM.handler.Broadcast(modem)

        r = handler.msg_received(proto, "dummy")
        assert r == Msg.UNKNOWN

        flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
        msg = Msg.InpStandard(addr, broadcast_to_addr, flags, 0x11, 0x01)

        # no device
        r = handler.msg_received(proto, msg)
        assert r == Msg.UNKNOWN

        device = IM.device.Base(proto, modem, addr, "foo")
        device.handle_broadcast = calls.append
        modem.add(device)
        r = handler.msg_received(proto, msg)

        assert r == Msg.CONTINUE
        assert len(calls) == 1

        # cleanup should be ignored since prev was processed.
        flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_CLEANUP, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x11, 0x01)
        r = handler.msg_received(proto, msg)

        assert r == Msg.CONTINUE
        assert len(calls) == 1

        # If broadcast wasn't found, cleanup should be handled.
        handler._last_broadcast = None
        r = handler.msg_received(proto, msg)

        assert r == Msg.CONTINUE
        assert len(calls) == 2

        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x11, 0x01)
        r = handler.msg_received(proto, msg)
        assert r == Msg.UNKNOWN

        # Success Report Broadcast
        flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
        success_report_to_addr = IM.Address(0x11, 1, 0x1)
        msg = Msg.InpStandard(addr, addr, flags, 0x06, 0x00)
        r = handler.msg_received(proto, msg)

        assert r == Msg.CONTINUE
        assert len(calls) == 3

        # Pretend that a new broadcast message dropped / not received by PLM

        # Cleanup should be handled since corresponding broadcast was missed
        flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_CLEANUP, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x13, 0x01)
        r = handler.msg_received(proto, msg)

        assert r == Msg.CONTINUE
        assert len(calls) == 4

    #-----------------------------------------------------------------------

#===========================================================================


class MockProto:
    def __init__(self):
        self.signal_received = IM.Signal()

    def add_handler(self, *args):
        pass

    def set_wait_time(self, *args):
        pass
