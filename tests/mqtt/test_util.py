#===========================================================================
#
# Tests for: insteont_mqtt/mqtt/util.py
#
#===========================================================================
import pytest
import insteon_mqtt as IM
import insteon_mqtt.mqtt.util as util


class Test_util:
    #-----------------------------------------------------------------------
    def test_parse_on_off_basic(self):
        data = {"cmd" : "ON"}
        is_on = util.parse_on_off(data, have_mode=False)
        assert is_on is True

        data = {"cmd" : "off"}
        is_on = util.parse_on_off(data, have_mode=False)
        assert is_on is False

        data = {"cmd" : "ON"}
        is_on, mode, transition = util.parse_on_off(data, have_mode=True)
        assert is_on is True
        assert mode is IM.on_off.Mode.NORMAL

        data = {"cmd" : "off"}
        is_on, mode, transition = util.parse_on_off(data, have_mode=True)
        assert is_on is False
        assert mode is IM.on_off.Mode.NORMAL

    #-----------------------------------------------------------------------
    def test_parse_on_off_mode(self):
        data = {"cmd" : "ON", "mode" : "NORMAL"}
        is_on = util.parse_on_off(data, have_mode=False)
        assert is_on is True

        is_on, mode, transition = util.parse_on_off(data)
        assert is_on is True
        assert mode is IM.on_off.Mode.NORMAL

        data = {"cmd" : "ON", "mode" : "faST"}
        is_on, mode, transition = util.parse_on_off(data)
        assert is_on is True
        assert mode is IM.on_off.Mode.FAST

        data = {"cmd" : "ON", "mode" : "instant"}
        is_on, mode, transition = util.parse_on_off(data)
        assert is_on is True
        assert mode is IM.on_off.Mode.INSTANT

    #-----------------------------------------------------------------------
    def test_parse_on_off_fast(self):
        data = {"cmd" : "ON", "fast" : 0}
        is_on, mode, transition = util.parse_on_off(data)
        assert is_on is True
        assert mode is IM.on_off.Mode.NORMAL

        data = {"cmd" : "ON", "fast" : 1}
        is_on, mode, transition = util.parse_on_off(data)
        assert is_on is True
        assert mode is IM.on_off.Mode.FAST

        data = {"cmd" : "ON", "fast" : True, "instant" : True}
        is_on, mode, transition = util.parse_on_off(data)
        assert is_on is True
        assert mode is IM.on_off.Mode.FAST

    #-----------------------------------------------------------------------
    def test_parse_on_off_instant(self):
        data = {"cmd" : "ON", "instant" : 0}
        is_on, mode, transition = util.parse_on_off(data)
        assert is_on is True
        assert mode is IM.on_off.Mode.NORMAL

        data = {"cmd" : "ON", "instant" : 1}
        is_on, mode, transition = util.parse_on_off(data)
        assert is_on is True
        assert mode is IM.on_off.Mode.INSTANT

        data = {"cmd" : "ON", "instant" : True}
        is_on, mode, transition = util.parse_on_off(data)
        assert is_on is True
        assert mode is IM.on_off.Mode.INSTANT

    #-----------------------------------------------------------------------
    def test_parse_on_off_transition(self):
        data = {"cmd" : "ON", "mode" : "ramp", "transition" : 5 }
        is_on, mode, transition = util.parse_on_off(data, have_mode=True)
        assert is_on is True
        assert mode is IM.on_off.Mode.RAMP
        assert transition is 5

        data = {"cmd" : "ON", "mode" : "ramp", "transition" : 0.5 }
        is_on, mode, transition = util.parse_on_off(data, have_mode=True)
        assert is_on is True
        assert mode is IM.on_off.Mode.RAMP
        assert transition is 0.5

        data = {"cmd" : "OFF", "mode" : "ramp", "transition" : 2 }
        is_on, mode, transition = util.parse_on_off(data, have_mode=True)
        assert is_on is False
        assert mode is IM.on_off.Mode.RAMP
        assert transition is 2

        data = {"cmd" : "ON", "transition" : 2 }
        is_on, mode, transition = util.parse_on_off(data, have_mode=True)
        assert is_on is True
        assert mode is IM.on_off.Mode.RAMP
        assert transition is 2

        data = {"cmd" : "OFF", "transition" : 480 }
        is_on, mode, transition = util.parse_on_off(data, have_mode=True)
        assert is_on is False
        assert mode is IM.on_off.Mode.RAMP
        assert transition is 480

    #-----------------------------------------------------------------------
    def test_parse_on_off_error(self):
        data = {"cmd" : "foo"}
        with pytest.raises(Exception):
            util.parse_on_off(data, have_mode=False)
