#===========================================================================
#
# Tests for: insteont_mqtt/config.py
#
# pylint: disable=attribute-defined-outside-init
#===========================================================================
import os
import glob
import pytest
from insteon_mqtt.Config import Config
import insteon_mqtt as IM


class Test_config:
    #-----------------------------------------------------------------------
    def test_basic(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'configs', 'basic.yaml')
        cfg = Config(file)
        (cls, args) = cfg.find("dimmer")
        assert cls == IM.device.Dimmer
        assert args == {}

        (cls, args) = cfg.find("mini_remote8")
        assert cls == IM.device.Remote
        assert args == {'num_button' : 8}

    #-----------------------------------------------------------------------
    def test_errors(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'configs', 'basic.yaml')
        cfg = Config(file)
        with pytest.raises(Exception):
            cfg.find("foo")

    #-----------------------------------------------------------------------
    def test_load(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'configs', 'basic.yaml')
        cfg = Config(file)
        assert "logging" in cfg.data
        assert "insteon" in cfg.data
        assert "mqtt" in cfg.data

    #-----------------------------------------------------------------------
    def test_apply(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'configs', 'basic.yaml')
        cfg = Config(file)

        mqtt = MockManager()
        modem = MockManager()
        Config.apply(cfg, mqtt, modem)

        assert mqtt.config == cfg
        assert modem.config == cfg

    #-----------------------------------------------------------------------
    def test_multi(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'configs', 'multi.yaml')
        cfg = Config(file)
        assert "logging" in cfg.data
        assert "insteon" in cfg.data
        assert "mqtt" in cfg.data

    #-----------------------------------------------------------------------
    def test_multi_error(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'configs', 'multi_error.yaml')
        with pytest.raises(Exception):
            Config(file)

    #-----------------------------------------------------------------------
    def test_basic_save(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'configs', 'basic.yaml')
        cfg = Config(file)
        cfg.save()
        assert not os.path.exists(cfg.backup)

    #-----------------------------------------------------------------------
    def test_save_backup(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'configs', 'basic.yaml')
        cfg = Config(file)
        cfg.data = []
        cfg.save()
        assert os.path.exists(cfg.backup)
        if os.path.exists(cfg.backup):
            os.remove(file)
            os.rename(cfg.backup, file)

#===========================================================================
class MockManager:
    def load_config(self, config):
        self.config = config
