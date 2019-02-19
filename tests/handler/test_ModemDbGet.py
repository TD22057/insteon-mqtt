#===========================================================================
#
# Tests for: insteont_mqtt/handler/ModemGetDb.py
#
# pylint: disable=attribute-defined-outside-init
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg


class Test_ModemDbGet:
    def test_acks(self):
        calls = []

        def callback(success, msg, done):
            calls.append(msg)

        proto = MockProtocol()
        db = Mockdb()
        handler = IM.handler.ModemDbGet(db, callback)

        get_first = Msg.OutAllLinkGetFirst(is_ack=True)
        get_next = Msg.OutAllLinkGetNext(is_ack=True)
        get_nak = Msg.OutAllLinkGetNext(is_ack=False)

        r = handler.msg_received(proto, get_first)
        assert r == Msg.CONTINUE

        r = handler.msg_received(proto, get_next)
        assert r == Msg.CONTINUE

        r = handler.msg_received(proto, get_nak)
        assert r == Msg.FINISHED
        assert calls == ['Database download complete']

        r = handler.msg_received(proto, "dummy")
        assert r == Msg.UNKNOWN

    #-----------------------------------------------------------------------
    def test_recs(self):
        calls = []

        def callback(success, msg, done):
            calls.append(msg)

        db = Mockdb()
        handler = IM.handler.ModemDbGet(db, callback)
        proto = MockProtocol()

        b = bytes([0x02, 0x57,
                   0xe2,  # flags
                   0x01,  # group
                   0x3a, 0x29, 0x84,  # addess
                   0x01, 0x0e, 0x43])  # data
        msg = Msg.InpAllLinkRec.from_bytes(b)
        test_entry = IM.db.ModemEntry(msg.addr, msg.group,
                                      msg.db_flags.is_controller, msg.data)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert isinstance(proto.sent, Msg.OutAllLinkGetNext)
        assert proto.handler == handler
        assert db.entry == test_entry

#===========================================================================


class MockProtocol:
    def send(self, msg, handler, high_priority=False, after=None):
        self.sent = msg
        self.handler = handler


class Mockdb:
    def save(self):
        pass

    def add_entry(self, entry):
        self.entry = entry
