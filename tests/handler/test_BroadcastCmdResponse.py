#===========================================================================
#
# Tests for: insteont_mqtt/handler/BroadcastCmdResponse.py
#
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg


class Test_BroadcastCmdResponse:
    def test_cmd_from_msg(self):
        # Tests matching the command from the outbound message.
        proto = MockProto()
        calls = []

        def callback(msg, on_done=None):
            calls.append(msg)

        addr = IM.Address('0a.12.34')

        # sent message, match input command
        out = Msg.OutStandard.direct(addr, 0x10, 0x00)
        handler = IM.handler.BroadcastCmdResponse(out, callback)

        r = handler.msg_received(proto, "dummy")
        assert r == Msg.UNKNOWN

        # ack back.
        out.is_ack = False
        r = handler.msg_received(proto, out)
        assert r == Msg.CONTINUE

        # wrong cmd
        out.cmd1 = 0x13
        r = handler.msg_received(proto, out)
        assert r == Msg.UNKNOWN

        # wrong addr
        out.cmd1 = 0x11
        out.to_addr = IM.Address('0a.12.33')
        r = handler.msg_received(proto, out)
        assert r == Msg.UNKNOWN

        # Now pass in the input message.

        # expected input meesage
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x10, 0x00)

        r = handler.msg_received(proto, msg)
        assert r == Msg.CONTINUE

        # wrong cmd
        msg.cmd1 = 0x13
        r = handler.msg_received(proto, msg)
        assert r == Msg.UNKNOWN

        # wrong addr
        msg.cmd1 = 0x11
        msg.from_addr = IM.Address('0a.12.33')
        r = handler.msg_received(proto, msg)
        assert r == Msg.UNKNOWN

        # direct NAK
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_NAK, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x10, 0x00)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED

        # unexpected
        flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x10, 0x00)
        r = handler.msg_received(proto, msg)
        assert r == Msg.UNKNOWN

        # Test receipt of broadcast payloads
        flags = Msg.Flags(Msg.Flags.Type.BROADCAST, False)
        # cmd1 doesn't have to match cmd1 of sent message
        msg = Msg.InpStandard(addr, addr, flags, 0x01, 0x00)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert len(calls) == 1
        assert calls[0] == msg

        # Test receipt of bad payloads
        msg.from_addr = IM.Address('0a.12.33')
        r = handler.msg_received(proto, msg)
        assert r == Msg.UNKNOWN


#===========================================================================


class MockProto:
    def add_handler(self, *args):
        pass
