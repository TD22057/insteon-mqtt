#===========================================================================
#
# Tests for: insteont_mqtt/message/Base.py
#
#===========================================================================
import pytest
import insteon_mqtt.message as Msg


class Test_Base:
    #-----------------------------------------------------------------------
    def test_errors(self):
        obj = Msg.Base()

        with pytest.raises(NotImplementedError):
            Msg.Base.from_bytes([])

        with pytest.raises(NotImplementedError):
            obj.msg_size([])

        Msg.Base.fixed_msg_size = 10
        assert obj.msg_size([]) == 10

        with pytest.raises(NotImplementedError):
            obj.to_bytes()

    #-----------------------------------------------------------------------


#===========================================================================
