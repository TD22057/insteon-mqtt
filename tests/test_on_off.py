#===========================================================================
#
# Tests for: insteont_mqtt/on_off.py
#
#===========================================================================
import insteon_mqtt as IM
import pytest

#===========================================================================
def test_is_valid():
    for cmd in IM.on_off._cmdMap:
        assert IM.on_off.Mode.is_valid( cmd )

    assert not IM.on_off.Mode.is_valid( 0x00 )
    assert not IM.on_off.Mode.is_valid( 0x50 )


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
    assert on == True
    assert mode == IM.on_off.Mode.NORMAL
    str(mode)

    on, mode = IM.on_off.Mode.decode(0x12)
    assert on == True
    assert mode == IM.on_off.Mode.FAST
    str(mode)

    on, mode = IM.on_off.Mode.decode(0x21)
    assert on == True
    assert mode == IM.on_off.Mode.INSTANT
    str(mode)

    on, mode = IM.on_off.Mode.decode(0x23)
    assert on == True
    assert mode == IM.on_off.Mode.MANUAL
    str(mode)

    on, mode = IM.on_off.Mode.decode(0x13)
    assert on == False
    assert mode == IM.on_off.Mode.NORMAL
    str(mode)

    on, mode = IM.on_off.Mode.decode(0x14)
    assert on == False
    assert mode == IM.on_off.Mode.FAST
    str(mode)

    with pytest.raises(Exception):
        IM.on_off.Mode.decode(0xff)
