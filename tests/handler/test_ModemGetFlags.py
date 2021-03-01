#===========================================================================
#
# Tests for: insteont_mqtt/handler/ModemGetFlags.py
#
# pylint: disable=attribute-defined-outside-init
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg
import helpers as H


class Test_ModemGetFlags:
    def test_acks(self, tmpdir):
        calls = []

        def callback(success, msg, done):
            calls.append((success, msg, done))

        modem = H.main.MockModem(tmpdir)
        proto = H.main.MockProtocol()
        handler = IM.handler.ModemGetFlags(modem, callback)
        handler._PLM_sent = True
        handler._PLM_ACK = True

        #Try a good message
        msg = Msg.OutGetModemFlags(is_ack=True, modem_flags=0x01, spare1=0x02,
                                   spare2=0x03)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert calls[0][0]

        #Try a NAK message
        msg = Msg.OutGetModemFlags(is_ack=False, modem_flags=0x01, spare1=0x02,
                                   spare2=0x03)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert not calls[1][0]

        #Wrong Message
        msg = Msg.OutResetModem(is_ack=True)
        r = handler.msg_received(proto, msg)
        assert r == Msg.UNKNOWN

    #-----------------------------------------------------------------------
    def test_plm_sent(self, tmpdir):
        calls = []

        def callback(success, msg, done):
            calls.append((success, msg, done))

        modem = H.main.MockModem(tmpdir)
        proto = H.main.MockProtocol()
        handler = IM.handler.ModemGetFlags(modem, callback)
        assert not handler._PLM_sent

        #Try a message prior to sent
        msg = Msg.OutGetModemFlags(is_ack=False, modem_flags=0x01, spare1=0x02,
                                   spare2=0x03)
        r = handler.msg_received(proto, msg)
        assert r == Msg.UNKNOWN

        # Signal Sent
        handler.sending_message(msg)
        assert handler._PLM_sent

        #Try a message prior to sent
        msg = Msg.OutGetModemFlags(is_ack=False, modem_flags=0x01, spare1=0x02,
                                   spare2=0x03)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
