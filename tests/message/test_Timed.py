#===========================================================================
#
# Tests for: insteont_mqtt/message/Timed.py
#
#===========================================================================
from unittest import mock
import insteon_mqtt as IM


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
        msg = mock.Mock()
        msg.to_bytes.return_value = "123"
        handler = mock.Mock()
        obj = IM.message.Timed(msg, handler, False, t0)

        link = mock.Mock()
        protocol = IM.Protocol(link)

        obj.send(protocol)

        last = link.mock_calls[-1]
        assert last == mock.call.write("123", 0)

    #-----------------------------------------------------------------------


#===========================================================================
