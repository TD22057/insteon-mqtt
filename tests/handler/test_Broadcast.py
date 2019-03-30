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
        modem = IM.Modem(proto)
        modem.save_path = str(tmpdir)

        addr = IM.Address('0a.12.34')
        handler = IM.handler.Broadcast(modem)

        r = handler.msg_received(proto, "dummy")
        assert r == Msg.UNKNOWN

        flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x11, 0x01)

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
        handler._handled = False
        r = handler.msg_received(proto, msg)

        assert r == Msg.CONTINUE
        assert len(calls) == 2

        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x11, 0x01)
        r = handler.msg_received(proto, msg)
        assert r == Msg.UNKNOWN

    #-----------------------------------------------------------------------

#===========================================================================


class MockProto:
    def __init__(self):
        self.signal_received = IM.Signal()

    def add_handler(self, *args):
        pass
