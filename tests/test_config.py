#===========================================================================
#
# Tests for: insteont_mqtt/config.py
#
# pylint: disable=attribute-defined-outside-init
#===========================================================================
import os
import pytest
import insteon_mqtt as IM


class Test_config:
    #-----------------------------------------------------------------------
    def test_basic(self):
        (cls, args) = IM.config.find("dimmer")
        assert cls == IM.device.Dimmer
        assert args == {}

        (cls, args) = IM.config.find("mini_remote8")
        assert cls == IM.device.Remote
        assert args == {'num_button' : 8}

    #-----------------------------------------------------------------------
    def test_errors(self):
        with pytest.raises(Exception):
            IM.config.find("foo")

    #-----------------------------------------------------------------------
    def test_load(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'configs', 'basic.yaml')
        cfg = IM.config.load(file)
        assert "logging" in cfg
        assert "insteon" in cfg
        assert "mqtt" in cfg

    #-----------------------------------------------------------------------
    def test_apply(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'configs', 'basic.yaml')
        cfg = IM.config.load(file)

        mqtt = MockManager()
        modem = MockManager()
        IM.config.apply(cfg, mqtt, modem)

        assert mqtt.config == cfg["mqtt"]
        assert modem.config == cfg["insteon"]

    #-----------------------------------------------------------------------
    def test_multi(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'configs', 'multi.yaml')
        cfg = IM.config.load(file)
        assert "logging" in cfg
        assert "insteon" in cfg
        assert "mqtt" in cfg

    #-----------------------------------------------------------------------
    def test_multi_error(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'configs', 'multi_error.yaml')
        with pytest.raises(Exception):
            IM.config.load(file)


#===========================================================================
class MockManager:
    def load_config(self, config):
        self.config = config
