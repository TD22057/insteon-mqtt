#===========================================================================
#
# Tests for: insteont_mqtt/device/Dimmer.py
#
#===========================================================================
import pytest
import time
# from pprint import pprint
from unittest import mock
from unittest.mock import call
import insteon_mqtt as IM
import insteon_mqtt.device.Dimmer as Dimmer
import insteon_mqtt.message as Msg
import insteon_mqtt.util as util
import helpers as H

@pytest.fixture
def test_device(tmpdir):
    '''
    Returns a generically configured dimmer for testing
    '''
    protocol = H.main.MockProtocol()
    modem = H.main.MockModem(tmpdir)
    addr = IM.Address(0x01, 0x02, 0x03)
    device = Dimmer(protocol, modem, addr)
    return device


class Test_Scene_Function():
    @pytest.mark.parametrize("is_on,group,level", [
        (True, 0x01, None),
        (True, None, None),
        (True, 0x01, 128),
        (False, None, None),
    ])
    def test_scene(self, test_device, is_on, group, level):
        test_device.scene(is_on, group=group, level=level)

        # test the message contents
        if group is None:
            group = 0x01
        assert len(test_device.protocol.sent) == 1
        assert test_device.protocol.sent[0].msg.cmd1 == 0x30
        assert test_device.protocol.sent[0].msg.cmd2 == 0x00
        assert test_device.protocol.sent[0].msg.data[0] == group # group
        if level is None:
            # don't use_on_level
            if is_on:
                assert test_device.protocol.sent[0].msg.data[1] == 0x00
            else:
                # off always 0x01
                assert test_device.protocol.sent[0].msg.data[1] == 0x01
            assert test_device.protocol.sent[0].msg.data[2] == 0x00
        else:
            # use_on_level
            assert test_device.protocol.sent[0].msg.data[1] == 0x01
            assert test_device.protocol.sent[0].msg.data[2] == int(level)
        if is_on:
            assert test_device.protocol.sent[0].msg.data[3] == 0x11
        else:
            assert test_device.protocol.sent[0].msg.data[3] == 0x13
        assert test_device.protocol.sent[0].msg.data[4] == 0x01
        assert test_device.protocol.sent[0].msg.data[5] == 0x00

        # Test the broadcast_scene_level contents
        test_device.protocol.sent[0].handler.on_done(True, None, None)
        scene_timestamp = test_device.broadcast_scene_level['timestamp'] + 1
        scene_level = test_device.broadcast_scene_level['level']
        if not is_on:
            assert scene_timestamp == 1
        elif level is None:
            assert scene_timestamp == 1
            assert scene_level == 0
        else:
            assert scene_timestamp >= time.time()
            assert scene_level == level
