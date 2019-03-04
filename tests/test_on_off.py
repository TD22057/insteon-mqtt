#===========================================================================
#
# Tests for: insteont_mqtt/on_off.py
#
# pylint: disable=protected-access
#===========================================================================
import pytest
import insteon_mqtt as IM


#===========================================================================
def test_is_valid():
    for cmd in IM.on_off._cmdMap:
        assert IM.on_off.Mode.is_valid(cmd)

    assert not IM.on_off.Mode.is_valid(0x00)
    assert not IM.on_off.Mode.is_valid(0x50)


#===========================================================================
def test_encode():
    on = IM.on_off.Mode.encode(True, IM.on_off.Mode.NORMAL)
    assert on == 0x11

    on = IM.on_off.Mode.encode(True, IM.on_off.Mode.FAST)
    assert on == 0x12

    on = IM.on_off.Mode.encode(True, IM.on_off.Mode.INSTANT)
    assert on == 0x21

    on = IM.on_off.Mode.encode(True, IM.on_off.Mode.MANUAL)
    assert on == 0x23

    on = IM.on_off.Mode.encode(False, IM.on_off.Mode.NORMAL)
    assert on == 0x13

    on = IM.on_off.Mode.encode(False, IM.on_off.Mode.FAST)
    assert on == 0x14

    on = IM.on_off.Mode.encode(False, IM.on_off.Mode.MANUAL)
    assert on == 0x22


#===========================================================================
def test_decode():
    on, mode = IM.on_off.Mode.decode(0x11)
    assert on is True
    assert mode == IM.on_off.Mode.NORMAL
    str(mode)

    on, mode = IM.on_off.Mode.decode(0x12)
    assert on is True
    assert mode == IM.on_off.Mode.FAST
    str(mode)

    on, mode = IM.on_off.Mode.decode(0x21)
    assert on is True
    assert mode == IM.on_off.Mode.INSTANT
    str(mode)

    on, mode = IM.on_off.Mode.decode(0x23)
    assert on is True
    assert mode == IM.on_off.Mode.MANUAL
    str(mode)

    on, mode = IM.on_off.Mode.decode(0x13)
    assert on is False
    assert mode == IM.on_off.Mode.NORMAL
    str(mode)

    on, mode = IM.on_off.Mode.decode(0x14)
    assert on is False
    assert mode == IM.on_off.Mode.FAST
    str(mode)

    with pytest.raises(Exception):
        IM.on_off.Mode.decode(0xff)


#===========================================================================
def test_manual_is_valid():
    for cmd in [0x17, 0x18]:
        assert IM.on_off.Manual.is_valid(cmd)

    assert not IM.on_off.Manual.is_valid(0x00)
    assert not IM.on_off.Manual.is_valid(0x50)


#===========================================================================
def test_manual_encode():
    cmd1, cmd2 = IM.on_off.Manual.encode(IM.on_off.Manual.UP)
    assert cmd1 == 0x17
    assert cmd2 == 0x01

    cmd1, cmd2 = IM.on_off.Manual.encode(IM.on_off.Manual.DOWN)
    assert cmd1 == 0x17
    assert cmd2 == 0x00

    cmd1, cmd2 = IM.on_off.Manual.encode(IM.on_off.Manual.STOP)
    assert cmd1 == 0x18
    assert cmd2 == 0x00


#===========================================================================
def test_manual_decode():
    mode = IM.on_off.Manual.decode(0x17, 0x01)
    assert mode == IM.on_off.Manual.UP
    str(mode)
    assert mode.int_value() == +1
    assert mode.openhab_value() == 2

    mode = IM.on_off.Manual.decode(0x17, 0x00)
    assert mode == IM.on_off.Manual.DOWN
    str(mode)
    assert mode.int_value() == -1
    assert mode.openhab_value() == 0

    mode = IM.on_off.Manual.decode(0x18, 0x00)
    assert mode == IM.on_off.Manual.STOP
    str(mode)
    assert mode.int_value() == 0
    assert mode.openhab_value() == 1

    with pytest.raises(Exception):
        IM.on_off.Manual.decode(0xff, 0x00)
