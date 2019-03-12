#===========================================================================
#
# Tests for: insteont_mqtt/Address.py
#
# pylint: disable=blacklisted-name, attribute-defined-outside-init
#===========================================================================
import pytest
import insteon_mqtt as IM


class Test_util:
    #-----------------------------------------------------------------------
    def test_to_hex(self):
        b = bytes([0x01, 0x08, 0xff, 0xa0, 0x0a])
        s = IM.util.to_hex(b)
        rt = "01 08 ff a0 0a"
        assert rt == s

    #-----------------------------------------------------------------------
    def test_to_hex_spc(self):
        b = bytes([0x01, 0x08, 0xff, 0xa0, 0x0a])
        s = IM.util.to_hex(b, space='.')
        rt = "01.08.ff.a0.0a"
        assert rt == s

    #-----------------------------------------------------------------------
    def test_to_hex_limit(self):
        b = bytes([0x01, 0x08, 0xff, 0xa0, 0x0a])
        s = IM.util.to_hex(b, 3)
        rt = "01 08 ff"
        assert rt == s

    #-----------------------------------------------------------------------
    def test_callback(self):
        cb = IM.util.make_callback(None)
        assert cb is not None
        cb(1, 2)

        def foo(*args):
            self._cb = args

        cb = IM.util.make_callback(foo)
        cb(1, 2)
        assert self._cb == (1, 2)

    #-----------------------------------------------------------------------
    def test_ctrl(self):
        r = IM.util.ctrl_str(True)
        assert r == "CTRL"

        r = IM.util.ctrl_str(False)
        assert r == "RESP"

    #-----------------------------------------------------------------------
    def test_bit_get(self):
        v = 0b0010
        assert IM.util.bit_get(v, 0) == 0
        assert IM.util.bit_get(v, 1) == 1
        assert IM.util.bit_get(v, 0) == 0
        assert IM.util.bit_get(v, 0) == 0

    #-----------------------------------------------------------------------
    def test_bit_set(self):
        v = 0b0010
        v = IM.util.bit_set(v, 0, 1)
        v = IM.util.bit_set(v, 1, 0)
        v = IM.util.bit_set(v, 2, 1)
        v = IM.util.bit_set(v, 3, 1)
        assert v == 0b1101

    #-----------------------------------------------------------------------
    def test_resolve3(self):
        # Use all inputs
        i = [1, 2, 3]
        d = [4, 5, 6]
        v = IM.util.resolve_data3(d, i)
        assert v == bytes([1, 2, 3])

        # Use all defaults
        i = [-1, -1, -1]
        d = [4, 5, 6]
        v = IM.util.resolve_data3(d, i)
        assert v == bytes([4, 5, 6])

        d = [4, 5, 6]
        v = IM.util.resolve_data3(d, None)
        assert v == bytes([4, 5, 6])

        # Use all mix
        i = [1, -1, 3]
        d = [4, 5, 6]
        v = IM.util.resolve_data3(d, i)
        assert v == bytes([1, 5, 3])

    #-----------------------------------------------------------------------
    def test_input_choice(self):
        inputs = {'key1' : 'VALUE1', 'key2' : 'value2'}
        choices = ['foo', 'bar', 'value1']
        v = IM.util.input_choice(inputs, 'key1', choices)
        assert v == 'value1'

        v = IM.util.input_choice(inputs, 'invalid', [])
        assert v is None

        with pytest.raises(ValueError):
            v = IM.util.input_choice(inputs, 'key2', ['foo', 'bar'])

    #-----------------------------------------------------------------------
    def test_input_bool(self):
        inputs = {'key1' : 'TRUE', 'key2' : 'FALSE',
                  'key3' : 1, 'key4': 0,
                  'key5' : 'On', 'key6' : 'Off',
                  'key7' : None, 'key8' : 'None',
                  'key9' : 'bad'}

        v = IM.util.input_bool(inputs, 'key1')
        assert v is True

        v = IM.util.input_bool(inputs, 'key2')
        assert v is False

        v = IM.util.input_bool(inputs, 'key3')
        assert v is True

        v = IM.util.input_bool(inputs, 'key4')
        assert v is False

        v = IM.util.input_bool(inputs, 'key5')
        assert v is True

        v = IM.util.input_bool(inputs, 'key6')
        assert v is False

        v = IM.util.input_bool(inputs, 'key7')
        assert v is None

        v = IM.util.input_bool(inputs, 'key8')
        assert v is None

        v = IM.util.input_bool(inputs, 'invalid')
        assert v is None

        with pytest.raises(ValueError):
            v = IM.util.input_bool(inputs, 'key9')

    #-----------------------------------------------------------------------
    def test_input_integer(self):
        inputs = {'key1' : '1', 'key2' : 2,
                  'key3' : '0x03', 'key4' : 0x04,
                  'key5' : None, 'key6' : 'None',
                  'key7' : '0b101', 'key8' : 'bad'}

        v = IM.util.input_integer(inputs, 'key1')
        assert v == 1

        v = IM.util.input_integer(inputs, 'key2')
        assert v == 2

        v = IM.util.input_integer(inputs, 'key3')
        assert v == 3

        v = IM.util.input_integer(inputs, 'key4')
        assert v == 4

        v = IM.util.input_integer(inputs, 'key5')
        assert v is None

        v = IM.util.input_integer(inputs, 'key6')
        assert v is None

        v = IM.util.input_integer(inputs, 'key7')
        assert v == 5

        v = IM.util.input_integer(inputs, 'invalid')
        assert v is None

        with pytest.raises(ValueError):
            v = IM.util.input_integer(inputs, 'key8')

    #-----------------------------------------------------------------------
    def test_input_byte(self):
        inputs = {'key1' : 0, 'key2' : '10',
                  'key3' : '0x2f', 'key4' : '0b11',
                  'key5' : 256, 'key6' : '257',
                  'key7' : 'bad'}

        v = IM.util.input_byte(inputs, 'missing')
        assert v is None

        v = IM.util.input_byte(inputs, 'key1')
        assert v == 0

        v = IM.util.input_byte(inputs, 'key2')
        assert v == 10

        v = IM.util.input_byte(inputs, 'key3')
        assert v == 0x2f

        v = IM.util.input_byte(inputs, 'key4')
        assert v == 0x03

        with pytest.raises(ValueError):
            v = IM.util.input_byte(inputs, 'key5')

        with pytest.raises(ValueError):
            v = IM.util.input_byte(inputs, 'key6')

        with pytest.raises(ValueError):
            v = IM.util.input_byte(inputs, 'key7')


#===========================================================================
