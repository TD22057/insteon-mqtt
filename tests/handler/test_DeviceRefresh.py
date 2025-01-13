#===========================================================================
#
# Tests for: insteon_mqtt/handler/DeviceRefresh.py
#
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg

class Test_DeviceRefresh:
    def test_acks(self):
        proto = None
        force = False
        refresh_msg = None
        calls = []

        def refresh_cb(msg):
            nonlocal refresh_msg
            refresh_msg = msg

        def done_cb(success, msg, value):
            calls.append(msg)

        modem_addr = IM.Address('09.12.34')
        dev_addr = IM.Address('0a.12.34')
        db_delta = 2
        device = MockDevice(dev_addr, db_delta)
        handler = IM.handler.DeviceRefresh(device, refresh_cb, force, done_cb)

        # Early device ACK, before PLM sent
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        early = Msg.InpStandard(dev_addr, modem_addr, flags, db_delta, 0x00)
        early.is_ack = True
        r = handler.msg_received(proto, early)
        assert r == Msg.UNKNOWN

        handler._PLM_sent = True

        # PLM NAK
        plm_nak = Msg.OutStandard.direct(dev_addr, 0x19, 0x00)
        plm_nak.is_ack = False
        r = handler.msg_received(proto, plm_nak)
        assert r == Msg.CONTINUE
        assert handler._PLM_ACK == False

        # PLM ACK
        plm_ack = Msg.OutStandard.direct(dev_addr, 0x19, 0x00)
        plm_ack.is_ack = True
        r = handler.msg_received(proto, plm_ack)
        assert r == Msg.CONTINUE
        assert handler._PLM_ACK == True

        # PLM ACK - wrong address
        nomatch = Msg.OutStandard.direct(IM.Address('0a.12.35'), 0x19, 0x00)
        nomatch.is_ack = True
        r = handler.msg_received(proto, nomatch)
        assert r == Msg.UNKNOWN

        # Now pass in the input message.

        # Direct NAK
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_NAK, False)
        msg = Msg.InpStandard(dev_addr, modem_addr, flags, 0x19, 0x00)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert len(calls) == 1
        assert calls[0] == "Device refresh failed. " + msg.nak_str()
        calls = []

        # Expected input message, DB up-to-date
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(dev_addr, modem_addr, flags, db_delta, 0x00)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert refresh_msg == msg
        assert len(calls) == 1
        assert calls[0] == "Refresh complete"
        calls = []

    def test_dbget_start(self):
        proto = None
        force = False
        refresh_msg = None
        calls = []

        def refresh_cb(msg):
            nonlocal refresh_msg
            refresh_msg = msg

        def done_cb(success, msg, value):
            calls.append(msg)

        modem_addr = IM.Address('09.12.34')
        dev_addr = IM.Address('0a.12.34')
        db_delta = 2
        device = MockDevice(dev_addr, db_delta)
        handler = IM.handler.DeviceRefresh(device, refresh_cb, force, done_cb)
        handler._PLM_sent = True
        handler._PLM_ACK = True

        # Expected input message, DB up-to-date, force update DB
        handler.force = True
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(dev_addr, modem_addr, flags, db_delta, 0x00)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert refresh_msg == msg
        assert len(calls) == 0
        # Assert DB-get message was sent
        db_download_msg = Msg.OutExtended.direct(dev_addr, 0x2f, 0x00,
                                                 bytes(14))
        assert len(device.sent) == 1
        assert (Msg.OutExtended.to_bytes(db_download_msg) ==
                Msg.OutExtended.to_bytes(device.sent[0]))
        device.sent = []
        # Reset force-update setting to initial value (False)
        handler.force = force

        # Expected input message, DB stale, skip_db
        handler.skip_db = True
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(dev_addr, modem_addr, flags, db_delta + 1, 0x00)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert refresh_msg == msg
        assert len(calls) == 1
        assert calls[0] == "Refresh complete"
        calls = []
        handler.skip_db = False

        # Expected input message, DB stale
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(dev_addr, modem_addr, flags, db_delta + 1, 0x00)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert refresh_msg == msg
        assert len(calls) == 0
        # Assert DB-get message was sent
        db_download_msg = Msg.OutExtended.direct(dev_addr, 0x2f, 0x00,
                                                 bytes(14))
        assert len(device.sent) == 1
        assert (Msg.OutExtended.to_bytes(db_download_msg) ==
                Msg.OutExtended.to_bytes(device.sent[0]))
        device.sent = []

        # Expected input message, DB stale (i1 device)
        device.db.engine = 0 # i1 device engine
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(dev_addr, modem_addr, flags, db_delta + 1, 0x00)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert refresh_msg == msg
        assert len(calls) == 0
        # Assert first set-MSB message was sent
        set_msb = Msg.OutStandard.direct(dev_addr, 0x28, 0x0F)
        assert len(device.sent) == 1
        assert (Msg.OutStandard.to_bytes(set_msb) ==
                Msg.OutStandard.to_bytes(device.sent[0]))
        device.sent = []
        device.db.engine = None # Reset to unknown engine

    def test_dbget_finish(self):
        proto = None
        force = False
        refresh_msg = None
        calls = []

        def refresh_cb(msg):
            nonlocal refresh_msg
            refresh_msg = msg

        def done_cb(success, msg, value):
            calls.append(msg)

        modem_addr = IM.Address('09.12.34')
        dev_addr = IM.Address('0a.12.34')
        db_delta = 2
        device = MockDevice(dev_addr, db_delta)
        handler = IM.handler.DeviceRefresh(device, refresh_cb, force, done_cb)
        handler._PLM_sent = True
        handler._PLM_ACK = True

        # Expected input message, DB stale
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(dev_addr, modem_addr, flags, db_delta + 1, 0x00)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert refresh_msg == msg
        assert len(calls) == 0
        # Assert DB-get message was sent
        db_download_msg = Msg.OutExtended.direct(dev_addr, 0x2f, 0x00,
                                                 bytes(14))
        assert len(device.sent) == 1
        assert (Msg.OutExtended.to_bytes(db_download_msg) ==
                Msg.OutExtended.to_bytes(device.sent[0]))
        device.sent = []

        # Get ahold of DeviceDbGet object created by DeviceRefresh
        assert len(device.handlers) == 1
        dbget_handler = device.handlers[0]
        assert isinstance(dbget_handler, IM.handler.DeviceDbGet)
        device.handlers = []

        # Simulate DB download complete
        dbget_handler._PLM_sent = True
        dbget_handler._PLM_ACK = True
        flags = Msg.Flags(Msg.Flags.Type.DIRECT, True)
        data = bytes([0x01, 0, 0x0F, 0xFF, 0, 0x0, 0, 0x01, 0, 0, 0, 0, 0, 0])
        msg = Msg.InpExtended(dev_addr, modem_addr, flags, 0x2f, 0x00, data)

        r = dbget_handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert len(calls) == 1
        assert calls[0] == "Database received"
        assert len(device.sent) == 0
        calls = []
        db_delta += 1
        assert device.db.delta == db_delta

        # Expected input message, DB stale
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(dev_addr, modem_addr, flags, db_delta + 1, 0x00)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert refresh_msg == msg
        assert len(calls) == 0
        # Assert DB-get message was sent
        db_download_msg = Msg.OutExtended.direct(dev_addr, 0x2f, 0x00,
                                                 bytes(14))
        assert len(device.sent) == 1
        assert (Msg.OutExtended.to_bytes(db_download_msg) ==
                Msg.OutExtended.to_bytes(device.sent[0]))
        device.sent = []

        # Get ahold of DeviceDbGet object created by DeviceRefresh
        assert len(device.handlers) == 1
        dbget_handler = device.handlers[0]
        assert isinstance(dbget_handler, IM.handler.DeviceDbGet)
        device.handlers = []

        # Simulate DB download incomplete
        # Only receive the first and last records, so DB is incomplete.
        dbget_handler._PLM_sent = True
        dbget_handler._PLM_ACK = True
        flags = Msg.Flags(Msg.Flags.Type.DIRECT, True)
        data = bytes([0x01, 0, 0x0F, 0xFF, 0, 0xFF, 0, 0x01, 0, 0, 0, 0, 0, 0])
        msg = Msg.InpExtended(dev_addr, modem_addr, flags, 0x2f, 0x00, data)

        r = dbget_handler.msg_received(proto, msg)
        assert r == Msg.CONTINUE
        assert len(calls) == 0

        data = bytes([0x01, 0, 0x0F, 0xEF, 0, 0x0, 0, 0x01, 0, 0, 0, 0, 0, 0])
        msg = Msg.InpExtended(dev_addr, modem_addr, flags, 0x2f, 0x00, data)

        r = dbget_handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert len(calls) == 0

        # Assert read-ALDB message sent for missing record
        mem_addr = 0xff7
        data = bytes([
            0x00,
            0x00,                   # ALDB record request
            mem_addr >> 8,          # Address MSB
            mem_addr & 0xff,        # Address LSB
            0x01,                   # Read one record
            ] + [0x00] * 9)
        read_rec = Msg.OutExtended.direct(dev_addr, 0x2f, 0x00, data)
        assert len(device.sent) == 1
        assert (Msg.OutStandard.to_bytes(read_rec) ==
                Msg.OutStandard.to_bytes(device.sent[0]))
        device.sent = []

#===========================================================================
class MockDevice:
    """Mock insteon_mqtt/Device class
    """
    def __init__(self, addr, db_delta):
        self.sent = []
        self.handlers = []
        self.addr = addr
        self.label = "MockDevice"
        self.db = IM.db.Device(addr, None, self)
        self.db.delta = db_delta

    def send(self, msg, handler, priority=None, after=None):
        self.sent.append(msg)
        self.handlers.append(handler)
