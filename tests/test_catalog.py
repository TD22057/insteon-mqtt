#===========================================================================
#
# Tests for: insteont_mqtt/catalog.py
#
#===========================================================================
import pytest
import insteon_mqtt as IM


class Test_catalog:
    def test_exists(self):
        assert IM.catalog.exists(0x01, 0x02) is True
        assert IM.catalog.exists(0x01, 0xff) is False
        assert IM.catalog.exists(0xff, 0xff) is False

    #-----------------------------------------------------------------------
    def test_find_good(self):
        d = IM.catalog.find(0x01, 0x02)
        assert d.dev_cat == 0x01
        assert d.sub_cat == 0x02
        assert d.model == "2475D"
        assert d.description == "In-LineLinc Dimmer"

    #-----------------------------------------------------------------------
    def test_find_bad(self):
        d = IM.catalog.find(0xff, 0x3a)
        assert d.dev_cat == 0xff
        assert d.sub_cat == 0x3a
        assert d.model == "Unknown"
        assert d.description == ""

        with pytest.raises(ValueError):
            IM.catalog.find(0xff, 0x1a, default=None)

    #-----------------------------------------------------------------------
    def test_find_all(self):
        items = IM.catalog.find_all(IM.catalog.Category.IRRIGATION)
        assert len(items) == 2
        for i in items:
            assert i.dev_cat == IM.catalog.Category.IRRIGATION

        items = IM.catalog.find_all(0xff)
        assert len(items) == 0

    #-----------------------------------------------------------------------
    def test_print(self):
        obj = IM.catalog.Entry(0x01, 0x02, "Model", "Desc")
        str(obj)

        obj = IM.catalog.Entry(0xff, 0x02)
        str(obj)
