#===========================================================================
#
# Tests for: insteont_mqtt/message/OutStandard.py
#
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg
import pytest

#===========================================================================
class Test_OutStandard:
    #-----------------------------------------------------------------------
    def test_basic(self):
        b = bytes([0x02, 0x62,  # code
                   0x48, 0x3d, 0x46,  # addr
                   0xaf,  # flags
                   0x11, 0xff,  # cmd1, cmd2
                   0x06])  # ack
        obj = Msg.OutStandard.from_bytes(b)

        assert obj.to_addr.ids == [0x48, 0x3d, 0x46]
        assert obj.flags.type == Msg.Flags.DIRECT_NAK
        assert obj.flags.is_ext == False
        assert obj.flags.hops_left == 3
        assert obj.flags.max_hops == 3
        assert obj.flags.is_nak == True
        assert obj.flags.is_broadcast == False
        assert obj.cmd1 == 0x11
        assert obj.cmd2 == 0xff
        assert obj.is_ack == True

        assert obj.msg_size(b) == Msg.OutStandard.fixed_msg_size

        ob = obj.to_bytes()
        assert ob == b[:-1]  # output has no ack

        str(obj)

    #-----------------------------------------------------------------------
    def test_direct(self):
        addr = IM.Address(0x48, 0x3d, 0x46)
        obj = Msg.OutStandard.direct(addr, 0x11, 0x25)

        assert obj.to_addr.ids == [0x48, 0x3d, 0x46]
        assert obj.flags.type == Msg.Flags.DIRECT
        assert obj.flags.is_ext == False
        assert obj.flags.hops_left == 3
        assert obj.flags.max_hops == 3
        assert obj.flags.is_nak == False
        assert obj.flags.is_broadcast == False
        assert obj.cmd1 == 0x11
        assert obj.cmd2 == 0x25
        assert obj.is_ack is None

        str(obj)

    #-----------------------------------------------------------------------


#===========================================================================
