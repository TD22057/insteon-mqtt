#===========================================================================
#
# Tests for: insteont_mqtt/handler/ModemGetDb.py
#
# pylint: disable=attribute-defined-outside-init
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg
import helpers as H


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
        db.device = MockDevice()
        handler = IM.handler.ModemDbGet(db, callback)
        proto = MockProtocol()

        b = bytes([0x02, 0x57,
                   0xe2,  # flags
                   0x01,  # group
                   0x3a, 0x29, 0x84,  # addess
                   0x01, 0x0e, 0x43])  # data
        msg = Msg.InpAllLinkRec.from_bytes(b)
        test_entry = IM.db.ModemEntry(msg.addr, msg.group,
                                      msg.db_flags.is_controller, msg.data,
                                      db=None)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert isinstance(db.device.sent[0]['msg'], Msg.OutAllLinkGetNext)
        assert db.device.sent[0]['handler'] == handler
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

class MockDevice:
    """Mock insteon_mqtt/Device class
    """
    def __init__(self):
        self.sent = []

    def send(self, msg, handler, priority=None, after=None):
        self.sent.append(H.Data(msg=msg, handler=handler))
