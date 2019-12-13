#===========================================================================
#
# Tests for: insteont_mqtt/mqtt/config.py
#
#===========================================================================
import insteon_mqtt as IM
import helpers as H


class Test_config:
    #-----------------------------------------------------------------------
    def test_find(self, tmpdir):
        proto = H.main.MockProtocol()
        modem = H.main.MockModem(tmpdir)
        addr = IM.Address(1, 2, 3)

        types = ["BatterySensor", "Dimmer", "FanLinc", "IOLinc", "KeypadLinc",
                 "Leak", "Motion", "Outlet", "SmokeBridge", "Switch",
                 "Thermostat"]
        instances = []
        for t in types:
            dev = getattr(IM.device, t)
            assert dev
            inst = dev(proto, modem, addr, "dummy")
            instances.append(inst)

        types.append("Remote")
        inst = IM.device.Remote(proto, modem, addr, "dummy", 3)
        instances.append(inst)

        types.append("Modem")
        inst = IM.Modem(proto)
        instances.append(inst)

        for i in range(len(types)):
            mdev = getattr(IM.mqtt, types[i])
            assert mdev

            cdev = IM.mqtt.config.find(instances[i])
            assert cdev is mdev, "Finding device for type %s" % types[i]

#===========================================================================
