#===========================================================================
#
# Tests for: insteont_mqtt/db/DeviceScanManagerI2.py
#
#===========================================================================
import pytest
import insteon_mqtt as IM
import insteon_mqtt.message as Msg
from insteon_mqtt.db.Device import START_MEM_LOC

class Test_DeviceScanManagerI2:
    def test_start_scan(self):
        dev_addr = IM.Address('0a.12.34')
        device = MockDevice(dev_addr, 0)
        manager = IM.db.DeviceScanManagerI2(device, device.db)

        first_mem_addr = START_MEM_LOC
        data = bytes([
            0x00,
            0x00,                   # ALDB record request
            first_mem_addr >> 8,    # Address MSB
            first_mem_addr & 0xff,  # Address LSB
            0x01,                   # Read one record
            ] + [0x00] * 9)
        db_msg = Msg.OutExtended.direct(dev_addr, 0x2f, 0x00, data)

        manager.start_scan()
        assert device.sent[0].to_bytes() == db_msg.to_bytes()

    #-------------------------------------------------------------------
    @pytest.mark.parametrize("init_db,mem_addr,recv,exp_calls,next_addr", [
        # Have all but last record.  Receive it, making DB complete.
        ( [ [ 0x00, 0x00, 0x0f, 0xff, 0xff,
              0xff, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ],
            [ 0x00, 0x00, 0x0f, 0xf7, 0xff,
              0xff, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ],
            [ 0x00, 0x00, 0x0f, 0xef, 0xff,
              0xff, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ] ],
          None,
          [ 0x00, 0x01, 0x0f, 0xe7, 0xff,
            0x00, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ],
          [ "Database received" ],
          None ),
        # Have all but third record.  Receive it, making DB complete.
        ( [ [ 0x00, 0x00, 0x0f, 0xff, 0xff,
              0xff, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ],
            [ 0x00, 0x00, 0x0f, 0xf7, 0xff,
              0xff, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ],
            [ 0x00, 0x00, 0x0f, 0xe7, 0xff,
              0x00, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ] ],
          None,
          [ 0x00, 0x01, 0x0f, 0xef, 0xff,
            0xff, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ],
          [ "Database received" ],
          None ),
        # Have first two records.  Receive third and request fourth.
        ( [ [ 0x00, 0x00, 0x0f, 0xff, 0xff,
              0xff, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ],
            [ 0x00, 0x00, 0x0f, 0xef, 0xff,
              0xff, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ] ],
          None,
          [ 0x00, 0x01, 0x0f, 0xf7, 0xff,
            0xff, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ],
          [ ],
          0xfe7 ),
        # Have first two records.  Receive last.  DB still incomplete.
        ( [ [ 0x00, 0x00, 0x0f, 0xff, 0xff,
              0xff, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ],
            [ 0x00, 0x00, 0x0f, 0xf7, 0xff,
              0xff, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ] ],
          None,
          [ 0x00, 0x01, 0x0f, 0xe7, 0xff,
            0x00, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ],
          [ "Database incomplete" ],
          None ),
        # Have first and last records.  Receive third.  DB still incomplete.
        ( [ [ 0x00, 0x00, 0x0f, 0xff, 0xff,
              0xff, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ],
            [ 0x00, 0x00, 0x0f, 0xe7, 0xff,
              0x00, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ] ],
          None,
          [ 0x00, 0x01, 0x0f, 0xef, 0xff,
            0xff, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ],
          [ "Database incomplete" ],
          None ),
        # Have first and last records.  Receive second and request third.
        ( [ [ 0x00, 0x00, 0x0f, 0xff, 0xff,
              0xff, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ],
            [ 0x00, 0x00, 0x0f, 0xe7, 0xff,
              0x00, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ] ],
          None,
          [ 0x00, 0x01, 0x0f, 0xf7, 0xff,
            0xff, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ],
          [ ],
          0xfef ),
        # Have first and last records.  Expecting second, but receive third.
        # Request second.
        ( [ [ 0x00, 0x00, 0x0f, 0xff, 0xff,
              0xff, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ],
            [ 0x00, 0x00, 0x0f, 0xe7, 0xff,
              0x00, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ] ],
          0xff7,
          [ 0x00, 0x01, 0x0f, 0xef, 0xff,
            0xff, 0x01, 0x0a, 0x12, 0x34, 0x00, 0x00, 0x00, 0x00 ],
          [ ],
          0xff7 )
    ])
    def test_handle_record(self, init_db, mem_addr, recv, exp_calls,
                           next_addr):
        calls = []

        def callback(success, msg, value):
            calls.append(msg)

        modem_addr = IM.Address('09.12.34')
        dev_addr = IM.Address('0a.12.34')
        device = MockDevice(dev_addr, 0)
        if mem_addr is None:
            # Expecting the same address that we're about to receive
            mem_addr = (recv[2] << 8) + recv[3]
        manager = IM.db.DeviceScanManagerI2(device, device.db, callback,
                                            mem_addr=mem_addr)

        # Initialize DB starting state
        for data in init_db:
            entry = IM.db.DeviceEntry.from_bytes(data, db=device.db)
            device.db.add_entry(entry)

        # Handle received message, check callbacks
        flags = Msg.Flags(Msg.Flags.Type.DIRECT, True)
        msg = Msg.InpExtended(dev_addr, modem_addr, flags, 0x2f, 0x00, recv)
        manager.handle_record(msg, callback)
        assert len(calls) == len(exp_calls)
        for idx, call in enumerate(exp_calls):
            assert calls[idx] == call

        # Check address of next requested entry (if any expected)
        if next_addr is not None:
            assert len(device.sent) == 1
            sent_data = device.sent[0].data
            requested_addr = (sent_data[2] << 8) + sent_data[3]
            assert requested_addr == next_addr

#===========================================================================
class MockDevice:
    """Mock insteon_mqtt/Device class
    """
    def __init__(self, addr, db_delta):
        self.sent = []
        self.addr = addr
        self.db = IM.db.Device(addr, None, self)
        self.db.delta = db_delta

    def send(self, msg, handler, priority=None, after=None):
        self.sent.append(msg)
