#===========================================================================
#
# Tests for: insteont_mqtt/handler/ModemGetDb.py
#
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg


class Test_ModemGetDb:
    def test_acks(self):
        calls = []
        def callback(msg):
            calls.append(msg)

        proto = MockProtocol()
        handler = IM.handler.ModemGetDb(callback)

        get_first = Msg.OutAllLinkGetFirst(is_ack=True)
        get_next = Msg.OutAllLinkGetNext(is_ack=True)
        get_nak = Msg.OutAllLinkGetNext(is_ack=False)

        r = handler.msg_received(proto, get_first)
        assert r == Msg.CONTINUE

        r = handler.msg_received(proto, get_next)
        assert r == Msg.CONTINUE

        r = handler.msg_received(proto, get_nak)
        assert r == Msg.FINISHED
        assert calls == [None]

        r = handler.msg_received(proto, "dummy")
        assert r == Msg.UNKNOWN

    #-----------------------------------------------------------------------
    def test_recs(self):
        calls = []
        def callback(msg):
            calls.append(msg)

        handler = IM.handler.ModemGetDb(callback)
        proto = MockProtocol()

        b = bytes([0x02, 0x57,
                   0xe2,  # flags
                   0x01,  # group
                   0x3a, 0x29, 0x84,  # addess
                   0x01, 0x0e, 0x43])  # data
        msg = Msg.InpAllLinkRec.from_bytes(b)

        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert isinstance(proto.sent, Msg.OutAllLinkGetNext)
        assert proto.handler == handler
        assert calls == [msg]

#===========================================================================


class MockProtocol:
    def send(self, msg, handler):
        self.sent = msg
        self.handler = handler
