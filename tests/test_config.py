#===========================================================================
#
# Tests for: insteont_mqtt/config.py
#
#===========================================================================
import insteon_mqtt as IM
import pytest


class Test_config:
    #-----------------------------------------------------------------------
    def test_basic(self):
        (cls, args)= IM.config.find("dimmer")
        assert cls == IM.device.Dimmer

        cls = IM.config.find("mini_remote8")

    #-----------------------------------------------------------------------
    def test_errors(self):
        with pytest.raises(Exception):
            IM.config.find("foo")

    #-----------------------------------------------------------------------


#===========================================================================
