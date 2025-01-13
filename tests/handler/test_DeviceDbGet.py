#===========================================================================
#
# Tests for: insteon_mqtt/handler/DeviceDbGet.py
#
#===========================================================================
import pytest
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
        handler._PLM_sent = True
        handler._PLM_ACK = True

        # Direct NAK
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_NAK, False)
        nak = Msg.InpStandard(addr, addr, flags, 0x2f, 0x00)
        r = handler.msg_received(proto, nak)
        assert r == Msg.FINISHED
        assert len(calls) == 1
        assert calls[0] == "Database command NAK. " + nak.nak_str()
        calls = []

        # Direct ACK
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        std_ack = Msg.InpStandard(addr, addr, flags, 0x2f, 0x00)
        r = handler.msg_received(proto, std_ack)
        assert r == Msg.CONTINUE

        # Direct ACK - wrong address
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        bad_addr = IM.Address('0a.12.35')
        nomatch = Msg.InpStandard(bad_addr, addr, flags, 0x2f, 0x00)
        nomatch.is_ack = True
        r = handler.msg_received(proto, nomatch)
        assert r == Msg.UNKNOWN

        # Direct ACK - wrong command
        std_ack.cmd1 = 0x11
        r = handler.msg_received(proto, std_ack)
        assert r == Msg.UNKNOWN

        # Direct ACK - wrong message type
        flags = Msg.Flags(Msg.Flags.Type.BROADCAST, False)
        bad_type = Msg.InpStandard(addr, addr, flags, 0x2f, 0x00)
        r = handler.msg_received(proto, bad_type)
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
        handler._PLM_sent = True
        handler._PLM_ACK = True

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

    #-----------------------------------------------------------------------
    @pytest.mark.parametrize("steps", [
        # Same example as test_recvs, except with real DB object
        ( [ { "data": [0x01, 0, 0, 0, 0, 0xFF, 0, 0x01, 0, 0, 0, 0, 0, 0],
              "r": Msg.CONTINUE, "calls": [] },
            { "data": bytes(14),
              "r": Msg.FINISHED, "calls": ["Database incomplete"] } ] ),
        # Receive three sequential records, ending with one marked "last".
        ( [ { "data": [0x01, 0, 0x0F, 0xFF, 0, 0xFF, 0, 0x01, 0, 0, 0, 0, 0, 0],
              "r": Msg.CONTINUE, "calls": [] },
            { "data": [0x01, 0, 0x0F, 0xF7, 0, 0xFF, 0, 0x01, 0, 0, 0, 0, 0, 0],
              "r": Msg.CONTINUE, "calls": [] },
            { "data": [0x01, 0, 0x0F, 0xEF, 0, 0x0, 0, 0x01, 0, 0, 0, 0, 0, 0],
              "r": Msg.FINISHED, "calls": ["Database received"] } ] ),
        # Only receive the first and last records, so DB is incomplete.
        ( [ { "data": [0x01, 0, 0x0F, 0xFF, 0, 0xFF, 0, 0x01, 0, 0, 0, 0, 0, 0],
              "r": Msg.CONTINUE, "calls": [] },
            { "data": [0x01, 0, 0x0F, 0xEF, 0, 0x0, 0, 0x01, 0, 0, 0, 0, 0, 0],
              "r": Msg.FINISHED, "calls": ["Database incomplete"] } ] ),
    ])
    def test_db_complete(self, steps):
        proto = None
        calls = []

        def callback(success, msg, value):
            calls.append(msg)

        addr = IM.Address('0a.12.34')
        db_delta = 2
        device = MockDevice(addr, db_delta)

        handler = IM.handler.DeviceDbGet(device.db, callback)
        handler._PLM_sent = True
        handler._PLM_ACK = True
        flags = Msg.Flags(Msg.Flags.Type.DIRECT, True)

        for step in steps:
            data = step["data"]
            msg = Msg.InpExtended(addr, addr, flags, 0x2f, 0x00, data)

            r = handler.msg_received(proto, msg)
            assert r == step["r"]
            assert len(calls) == len(step["calls"])
            for idx, call in enumerate(step["calls"]):
                assert calls[idx] == call

    #-----------------------------------------------------------------------
    def test_plm_sent_ack(self):
        proto = None
        calls = []

        def callback(success, msg, value):
            calls.append(msg)

        addr = IM.Address('0a.12.34')
        db = Mockdb(addr)
        handler = IM.handler.DeviceDbGet(db, callback)

        # test not sent
        std_ack = Msg.OutStandard.direct(addr, 0x2f, 0x00)
        std_ack.is_ack = True
        r = handler.msg_received(proto, std_ack)
        assert r == Msg.UNKNOWN

        # Signal Sent
        handler.sending_message(std_ack)
        assert handler._PLM_sent

        # PLM ACK - wrong address
        nomatch = Msg.OutStandard.direct(IM.Address('0a.12.35'), 0x2f, 0x00)
        nomatch.is_ack = True
        r = handler.msg_received(proto, nomatch)
        assert r == Msg.UNKNOWN

        # PLM NAK
        plm_nak = Msg.OutStandard.direct(addr, 0x2f, 0x00)
        plm_nak.is_ack = False
        r = handler.msg_received(proto, plm_nak)
        assert r == Msg.CONTINUE
        assert handler._PLM_ACK == False

        # PLM ACK
        std_ack = Msg.OutStandard.direct(addr, 0x2f, 0x00)
        std_ack.is_ack = True
        r = handler.msg_received(proto, std_ack)
        assert r == Msg.CONTINUE
        assert handler._PLM_ACK




#===========================================================================
class Mockdb:
    def __init__(self, addr):
        self.addr = addr

    def is_complete(self):
        return True

class MockDevice:
    """Mock insteon_mqtt/Device class
    """
    def __init__(self, addr, db_delta):
        self.sent = []
        self.addr = addr
        self.db = IM.db.Device(addr, None, self)
        self.db.delta = db_delta

    def send(self, msg, handler, priority=None, after=None):
        self.sent.append(H.Data(msg=msg, handler=handler))
