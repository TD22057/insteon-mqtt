#===========================================================================
#
# Tests for: insteont_mqtt/handler/StandardCmd.py
#
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg


class Test_StandardCmd:
    def test_cmd_from_msg(self):
        # Tests matching the command from the outbound message.
        proto = MockProto()
        calls = []

        def callback(msg, on_done=None):
            calls.append(msg)

        addr = IM.Address('0a.12.34')

        # sent message, match input command
        out = Msg.OutStandard.direct(addr, 0x11, 0xff)
        handler = IM.handler.StandardCmd(out, callback)

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
        msg = Msg.InpStandard(addr, addr, flags, 0x11, 0x01)

        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert len(calls) == 1
        assert calls[0] == msg

        # wrong cmd
        msg.cmd1 = 0x13
        r = handler.msg_received(proto, msg)
        assert r == Msg.UNKNOWN

        # wrong addr
        msg.cmd1 = 0x11
        msg.from_addr = IM.Address('0a.12.33')
        r = handler.msg_received(proto, msg)
        assert r == Msg.UNKNOWN

    #-----------------------------------------------------------------------
    def test_input_cmd(self):
        # Tests matching the command passed in.
        proto = MockProto()
        calls = []

        def callback(msg, on_done=None):
            calls.append(msg)

        addr = IM.Address('0a.12.34')

        # sent message, match input command
        out = Msg.OutStandard.direct(addr, 0x11, 0xff)
        handler = IM.handler.StandardCmd(out, callback)

        # right cmd
        r = handler.msg_received(proto, out)
        assert r == Msg.CONTINUE

        # wrong cmd
        out.cmd1 = 0x13
        r = handler.msg_received(proto, out)
        assert r == Msg.UNKNOWN

        # Now pass in the input message.
        # expected input meesage
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x11, 0x01)

        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert len(calls) == 1
        assert calls[0] == msg

    #-----------------------------------------------------------------------
    def test_any_cmd(self):
        # Tests matching any command
        proto = MockProto()
        calls = []

        def callback(msg, on_done=None):
            calls.append(msg)

        addr = IM.Address('0a.12.34')

        # sent message, match input command
        out = Msg.OutStandard.direct(addr, 0x11, 0x00)
        handler = IM.handler.StandardCmd(out, callback)

        r = handler.msg_received(proto, out)
        assert r == Msg.CONTINUE

        # Now pass in the input message.

        # expected input meesage
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x11, 0x01)

        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert len(calls) == 1
        assert calls[0] == msg

    #-----------------------------------------------------------------------
    def test_engine_version(self, tmpdir):
        # Tests response to get engine version
        proto = MockProto()
        modem = MockModem(tmpdir)
        calls = []
        addr = IM.Address('0a.12.34')
        device = IM.device.Base(proto, modem, addr)

        def callback(success, msg, data):
            calls.append(msg)

        # i1 test
        out = Msg.OutStandard.direct(addr, 0x0D, 0x00)
        handler = IM.handler.StandardCmd(out, device.handle_engine, callback)
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x0D, 0x00)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert calls[0] == "Operation complete"
        assert device.db.engine == 0

        #i2
        msg = Msg.InpStandard(addr, addr, flags, 0x0D, 0x01)
        r = handler.msg_received(proto, msg)
        assert device.db.engine == 1

        #i2cs
        msg = Msg.InpStandard(addr, addr, flags, 0x0D, 0x02)
        r = handler.msg_received(proto, msg)
        assert device.db.engine == 2


#===========================================================================


class MockProto:
    def add_handler(self, *args):
        pass


class MockModem:
    def __init__(self, path):
        self.save_path = str(path)
