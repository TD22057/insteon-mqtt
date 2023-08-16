#===========================================================================
#
# Tests for: insteont_mqtt/device/base/ResponderBase.py
#
# pylint: disable=W0621,W0212,
#
#===========================================================================
import logging
from pathlib import Path
# from pprint import pprint
from unittest import mock
from unittest.mock import call
import pytest
import insteon_mqtt as IM
from insteon_mqtt.device.base.ResponderBase import ResponderBase
from insteon_mqtt.device.base import Base
import insteon_mqtt.message as Msg
import insteon_mqtt.handler as Handler
import insteon_mqtt.on_off as on_off
import helpers as H

@pytest.fixture
def test_device(tmpdir):
    '''
    Returns a generically configured device for testing
    '''
    protocol = H.main.MockProtocol()
    modem = H.main.MockModem(tmpdir)
    modem.db = IM.db.Modem(None, modem)
    modem.scenes = IM.Scenes.SceneManager(modem, None)
    addr = IM.Address(0x01, 0x02, 0x03)
    device = ResponderBase(protocol, modem, addr)
    return device

class Test_ResponderBase_Cmds():
    ## On Command
    @pytest.mark.parametrize("mode_arg,cmd1", [
        (None, 0x11), # mode not set
        (on_off.Mode.INSTANT, 0x21), # mode as enum
        ("instant", 0x21), # mode as str
        ("bad_mode", 0x11), # bad mode
    ])
    def test_on(self, test_device, mode_arg, cmd1):
        with mock.patch.object(Base, 'send') as mocked:
            if mode_arg is not None:
                test_device.on(mode=mode_arg)
            else:
                test_device.on()
            assert mocked.call_count == 1
            call_args = mocked.call_args_list
            assert isinstance(call_args[0].args[0], Msg.OutStandard)
            assert call_args[0].args[0].cmd1 == cmd1
            assert call_args[0].args[0].cmd2 == 0xFF
            assert isinstance(call_args[0].args[1], Handler.StandardCmd)

    ## Off Command
    @pytest.mark.parametrize("mode_arg,cmd1", [
        (None, 0x13), # mode not set
        (on_off.Mode.INSTANT, 0x21), # mode as enum
        ("instant", 0x21), # mode as str
        ("bad_mode", 0x13), # bad mode
    ])
    def test_off(self, test_device, mode_arg, cmd1):
        with mock.patch.object(Base, 'send') as mocked:
            if mode_arg is not None:
                test_device.off(mode=mode_arg)
            else:
                test_device.off()
            assert mocked.call_count == 1
            call_args = mocked.call_args_list
            assert isinstance(call_args[0].args[0], Msg.OutStandard)
            assert call_args[0].args[0].cmd1 == cmd1
            assert call_args[0].args[0].cmd2 == 0x00
            assert isinstance(call_args[0].args[1], Handler.StandardCmd)

    ## Set Command
    @pytest.mark.parametrize("mode_arg,is_on,level,cmd1,cmd2", [
        (None, None, None, 0x13, 0x00),
        (None, True, None, 0x11, 0xFF),
        (None, None, 0x50, 0x11, 0xFF),
        (on_off.Mode.INSTANT, None, None, 0x21, 0x00),
        ('instant', None, None, 0x21, 0x00),
    ],
    ids=['mode not set', 'testB id', 'level is set', 'mode is enum', 'mode is str'])
    def test_set(self, test_device, mode_arg, is_on, level, cmd1, cmd2):
        kwargs = {}
        with mock.patch.object(Base, 'send') as mocked:
            if mode_arg is not None:
                kwargs['mode'] = mode_arg
            if is_on is not None:
                kwargs['is_on'] = is_on
            if level is not None:
                kwargs['level'] = level
            test_device.set(**kwargs)
            assert mocked.call_count == 1
            call_args = mocked.call_args_list
            assert isinstance(call_args[0].args[0], Msg.OutStandard)
            assert call_args[0].args[0].cmd1 == cmd1
            assert call_args[0].args[0].cmd2 == cmd2
            assert isinstance(call_args[0].args[1], Handler.StandardCmd)