#===========================================================================
#
# Tests for: insteont_mqtt/handler/ModemInfo.py
#
# pylint: disable=attribute-defined-outside-init
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.message as Msg
import helpers as H


class Test_ModemInfo:
    def test_acks(self, tmpdir):
        calls = []

        def callback(success, msg, done):
            calls.append((success, msg, done))

        modem = H.main.MockModem(tmpdir)
        proto = H.main.MockProtocol()
        handler = IM.handler.ModemInfo(modem, callback)
        handler._PLM_sent = True
        handler._PLM_ACK = True

        #Try a good message
        msg = Msg.OutModemInfo(addr=IM.Address('11.22.33'), dev_cat=0x44,
                               sub_cat=0x55, firmware=0x66, is_ack=True)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
        assert calls[0][0]

        #Try a NAK message
        msg = Msg.OutModemInfo(addr=IM.Address('11.22.33'), dev_cat=0x44,
                               sub_cat=0x55, firmware=0x66, is_ack=False)
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
        handler = IM.handler.ModemInfo(modem, callback)
        assert not handler._PLM_sent

        #Try a message prior to sent
        msg = Msg.OutModemInfo(addr=IM.Address('11.22.33'), dev_cat=0x44,
                               sub_cat=0x55, firmware=0x66, is_ack=True)
        r = handler.msg_received(proto, msg)
        assert r == Msg.UNKNOWN

        # Signal Sent
        handler.sending_message(msg)
        assert handler._PLM_sent

        #Try a message prior to sent
        msg = Msg.OutModemInfo(addr=IM.Address('11.22.33'), dev_cat=0x44,
                               sub_cat=0x55, firmware=0x66, is_ack=True)
        r = handler.msg_received(proto, msg)
        assert r == Msg.FINISHED
