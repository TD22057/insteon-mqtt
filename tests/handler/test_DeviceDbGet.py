#===========================================================================
#
# Tests for: insteont_mqtt/handler/DeviceGetDb.py
#
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg


class Test_DeviceDbGet:
    def test_acks(self):
        proto = None
        calls = []

        def callback(success, msg, value):
            calls.append(msg)

        addr = IM.Address('0a.12.34')
        db = Mockdb(addr)
        handler = IM.handler.DeviceDbGet(db, callback)

        # Normal nak
        std_ack = Msg.OutStandard.direct(addr, 0x2f, 0x00)
        std_ack.is_ack = False
        r = handler.msg_received(proto, std_ack)
        assert r == Msg.CONTINUE

        # Wrong address
        nomatch = Msg.OutStandard.direct(IM.Address('0a.12.35'), 0x2f, 0x00)
        std_ack.is_ack = True
        r = handler.msg_received(proto, nomatch)
        assert r == Msg.UNKNOWN

        # Wrong command
        std_ack.cmd1 = 0x11
        r = handler.msg_received(proto, std_ack)
        assert r == Msg.UNKNOWN

        # direct Pre NAK
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_NAK, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x2f, 0xFC)
        r = handler.msg_received(proto, msg)
        assert r == Msg.CONTINUE

        # Try w/ an extended msg.
        ext_data = bytes(14)
        ext_ack = Msg.OutExtended.direct(addr, 0x2f, 0x00, ext_data)
        ext_ack.is_ack = True
        r = handler.msg_received(proto, ext_ack)
        assert r == Msg.CONTINUE

        r = handler.msg_received(proto, "dummy")
        assert r == Msg.UNKNOWN

        assert calls == []

    #-----------------------------------------------------------------------
    def test_recs(self):
        proto = None
        calls = []

        def callback(success, msg, value):
            calls.append(msg)

        addr = IM.Address('0a.12.34')
        db = Mockdb(addr)
        handler = IM.handler.DeviceDbGet(db, callback)

        flags = Msg.Flags(Msg.Flags.Type.DIRECT, True)
        data = bytes([0x01, 0, 0, 0, 0, 0xFF, 0, 0x01, 0, 0, 0, 0, 0, 0])
        msg = Msg.InpExtended(addr, addr, flags, 0x2f, 0x00, data)

        r = handler.msg_received(proto, msg)
        assert r == Msg.CONTINUE
        assert len(calls) == 0

        msg.data = bytes(14)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert len(calls) == 1
        assert calls[0] == "Database received"

        # no match
        msg.cmd1 = 0x00
        r = handler.msg_received(proto, msg)
        assert r == Msg.UNKNOWN


#===========================================================================
class Mockdb:
    def __init__(self, addr):
        self.addr = addr
