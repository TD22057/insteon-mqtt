#===========================================================================
#
# Tests for: insteont_mqtt/config.py
#
# pylint: disable=attribute-defined-outside-init
#===========================================================================
import os
import yaml
import pytest
from unittest import mock
from unittest.mock import call
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

    #-----------------------------------------------------------------------
    def test_validate_good(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'configs', 'basic.yaml')
        val = IM.config.validate(file)
        assert val == ""

    #-----------------------------------------------------------------------
    def test_validate_bad(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'configs', 'bad_plm.yaml')
        val = IM.config.validate(file)
        assert val != ""

    #-----------------------------------------------------------------------
    def test_validate_example(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            '..', 'config-example.yaml')
        val = IM.config.validate(file)
        assert val == ""

    #-----------------------------------------------------------------------
    def test_good_hub(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'configs', 'good_hub.yaml')
        val = IM.config.validate(file)
        assert val == ""

    #-----------------------------------------------------------------------
    def test_dns(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'configs', 'use_dns.yaml')
        val = IM.config.validate(file)
        assert val == ""

    #-----------------------------------------------------------------------
    def test_scenes_empty(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'configs', 'scenes_empty.yaml')
        val = IM.config.validate(file)
        assert val == ""

    #-----------------------------------------------------------------------
    def test_discovery_schema_good(self):
        file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'configs', 'discovery_schema_good.yaml')
        val = IM.config.validate(file)
        assert val == ""

    #-----------------------------------------------------------------------
    def test_discovery_schema_bad(self):
        configs = [
            ("discovery_schema_class_mixed.yaml", "'discovery_overrides' must not be present with 'discovery_entities'"),
            ("discovery_schema_device_discoverable_overrides.yaml", "'component', 'config' must not be present with 'discoverable'"),
            ("discovery_schema_device_unknown.yaml", "entry does not match a valid device entry format"),
        ]

        for config in configs:
            file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                'configs', config[0])
            val = IM.config.validate(file)
            assert config[1] in val

    #-----------------------------------------------------------------------
    def test_validate_addr(self):
        validator = IM.config.IMValidator()
        validator._error = mock.Mock()

        # Good
        validator._check_with_valid_insteon_addr('test_field', 'aabbcc')
        validator._error.assert_not_called()

        # Also good
        validator._check_with_valid_insteon_addr('test_field', 'aa.bb.cc')
        validator._error.assert_not_called()

        # Also good
        validator._check_with_valid_insteon_addr('test_field', 'aa bb cc')
        validator._error.assert_not_called()

        # Also good
        validator._check_with_valid_insteon_addr('test_field', 'aa:bb:cc')
        validator._error.assert_not_called()

        # Also good
        validator._check_with_valid_insteon_addr('test_field', 'aa:bb.cc')
        validator._error.assert_not_called()

        # Also good
        validator._check_with_valid_insteon_addr('test_field', '5522')
        validator._error.assert_not_called()

        # Also bad
        validator._check_with_valid_insteon_addr('test_field', 'Error')
        validator._error.assert_called_once()
        validator._error.reset_mock()

        # Also bad
        validator._check_with_valid_insteon_addr('test_field', 'aabbbcc')
        validator._error.assert_called_once()
        validator._error.reset_mock()

    #-----------------------------------------------------------------------
    def test_overlay(self):
        base = """
                root:
                  string: string
                  dict:
                    value1: value1
                    value2: value2
                absent: here"""
        user = """
                root:
                  string: new-string
                  dict:
                    value1: value1
                    value2:
                      new-sub: value2
                  new: new-key"""
        config = IM.config.overlay(yaml.load(base, yaml.SafeLoader),
                                   yaml.load(user, yaml.SafeLoader))
        assert config['root']['string'] == 'new-string'
        assert config['root']['dict']['value1'] == 'value1'
        assert config['root']['dict']['value2']['new-sub'] == 'value2'
        assert config['root']['new'] == 'new-key'
        assert config['absent'] == 'here'

#===========================================================================
class MockManager:
    def load_config(self, config):
        self.config = config
