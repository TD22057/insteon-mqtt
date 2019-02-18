#===========================================================================
#
# Tests for: insteont_mqtt/Address.py
#
#===========================================================================
import pytest
import insteon_mqtt as IM


class Test_Address:
    def check(self, addr, id):
        ids = [(id & 0xff0000) >> 16, (id & 0xff00) >> 8, (id & 0xff)]
        hex = "%02X.%02X.%02X" % tuple(ids)
        assert addr.id == id
        assert addr.ids == ids
        assert addr.bytes == bytes(ids)
        assert addr.hex == hex.lower()
        str(addr)

        b = addr.to_bytes()
        addr2 = IM.Address.from_bytes(b)
        assert addr2.id == addr.id
        assert addr2 == addr

        j = addr.to_json()
        addr3 = IM.Address.from_json(j)
        assert addr3.id == addr.id
        assert addr3 == addr

    #-----------------------------------------------------------------------
    def test_id(self):
        a = IM.Address(123456)
        self.check(a, 123456)

    #-----------------------------------------------------------------------
    def test_addr(self):
        a = IM.Address(123456)
        b = IM.Address(a)
        self.check(b, a.id)

    #-----------------------------------------------------------------------
    def test_str1(self):
        a = IM.Address('01e240')
        self.check(a, 123456)

    #-----------------------------------------------------------------------
    def test_str2(self):
        a = IM.Address('01E240')
        self.check(a, 123456)

    #-----------------------------------------------------------------------
    def test_str3(self):
        a = IM.Address('01.E2.40')
        self.check(a, 123456)

    #-----------------------------------------------------------------------
    def test_str4(self):
        a = IM.Address('01 E2 40')
        self.check(a, 123456)

    #-----------------------------------------------------------------------
    def test_str5(self):
        a = IM.Address('01:e2:40')
        self.check(a, 123456)

    #-----------------------------------------------------------------------
    def test_id3(self):
        a = IM.Address(0x01, 0xe2, 0x40)
        self.check(a, 123456)

    #-----------------------------------------------------------------------
    def test_cmp(self):
        a = IM.Address(0x01, 0xe2, 0x40)
        a1 = IM.Address(0x01, 0xe2, 0x40)
        b = IM.Address(0x01, 0xe2, 0x41)
        assert a < b
        assert b > a
        assert a == a1
        assert a != b

        d = {a : 1, b : 2}
        assert d[a] == 1
        assert d[b] == 2

    #-----------------------------------------------------------------------
    def test_errors(self):
        with pytest.raises(Exception):
            IM.Address(0x01, 0x02, None)

        with pytest.raises(Exception):
            IM.Address(0x01, None, 0x03)

        with pytest.raises(Exception):
            IM.Address(None, 0x02, 0x03)

        with pytest.raises(Exception):
            IM.Address(1000, 1, 1)

        with pytest.raises(Exception):
            IM.Address(1, 1000, 1)

        with pytest.raises(Exception):
            IM.Address(1, 1, 1000)

        with pytest.raises(Exception):
            IM.Address(2**31)

        with pytest.raises(Exception):
            IM.Address([1], 1, 1)

        with pytest.raises(Exception):
            IM.Address("foo bar")

        with pytest.raises(Exception):
            IM.Address({1 : 2})

#===========================================================================
