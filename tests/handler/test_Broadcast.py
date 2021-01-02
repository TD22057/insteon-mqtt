#===========================================================================
#
# Tests for: insteont_mqtt/handler/Broadcast.py
#
# pylint: disable=protected-access
#===========================================================================
import time
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
        assert len(calls) == 0

        flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
        msg = Msg.InpStandard(addr, broadcast_to_addr, flags, 0x11, 0x01)

        # no device
        r = handler.msg_received(proto, msg)
        assert r == Msg.UNKNOWN
        assert len(calls) == 0

        # test good broadcat
        assert proto.wait_time == 0
        device = IM.device.Base(proto, modem, addr, "foo")

        # add 10 device db entries for this group
        for count in range(10):
            e_addr = IM.Address(0x10, 0xab, count)
            db_flags = Msg.DbFlags(in_use=True, is_controller=True,
                                   is_last_rec=False)
            entry = IM.db.DeviceEntry(e_addr, 0x01, count, db_flags,
                                      bytes([0x01, 0x02, 0x03]))
            device.db.add_entry(entry)

        device.handle_broadcast = calls.append
        modem.add(device)
        r = handler.msg_received(proto, msg)

        assert r == Msg.CONTINUE
        assert len(calls) == 1
        # should be at least 5.5 seconds ahead
        assert proto.wait_time - time.time() > 5

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
        pre_success_time = proto.wait_time
        flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
        success_report_to_addr = IM.Address(0x11, 1, 0x1)
        msg = Msg.InpStandard(addr, addr, flags, 0x06, 0x00)
        r = handler.msg_received(proto, msg)

        assert r == Msg.CONTINUE
        assert len(calls) == 3
        # wait time should be cleared
        assert proto.wait_time < pre_success_time

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
        self.wait_time = 0

    def add_handler(self, *args):
        pass

    def set_wait_time(self, wait_time):
        self.wait_time = wait_time
