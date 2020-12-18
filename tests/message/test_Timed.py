#===========================================================================
#
# Tests for: insteont_mqtt/message/Timed.py
#
#===========================================================================
from unittest import mock
import insteon_mqtt as IM
import insteon_mqtt.message as Msg


class Test_Timed:
    #-----------------------------------------------------------------------
    def test_active(self):
        t0 = 1000
        obj = IM.message.Timed("msg", "handler", False, t0)

        assert obj.is_active(t0) is True
        assert obj.is_active(t0 + 0.1) is True
        assert obj.is_active(t0 - 0.1) is False

    #-----------------------------------------------------------------------
    def test_send(self):
        t0 = 1000
        addr = IM.Address(0x48, 0x3d, 0x46)
        msg = Msg.OutStandard.direct(addr, 0x11, 0x25)
        handler = mock.Mock()
        obj = IM.message.Timed(msg, handler, False, t0)

        link = mock.Mock()
        protocol = IM.Protocol(link)

        obj.send(protocol)

        last = link.mock_calls[-1]
        assert last == mock.call.write(msg.to_bytes(), 0)

    #-----------------------------------------------------------------------


#===========================================================================
