#===========================================================================
#
# Tests for: insteont_mqtt/device/Thermostat.py
#
#===========================================================================
import insteon_mqtt as IM
import insteon_mqtt.device.Thermostat as Thermo
import insteon_mqtt.message as Msg


class Test_Thermostat:
    def test_basic(self, tmpdir):
        protocol = MockProto()
        modem = MockModem(tmpdir)
        addr = IM.Address(0x01, 0x02, 0x03)
        thermo = Thermo(protocol, modem, addr)

        # setup signal tracking
        thermo.signal_ambient_temp_change.connect(
            self.handle_ambient_temp_change)
        thermo.signal_fan_mode_change.connect(self.handle_fan_mode_change)
        thermo.signal_mode_change.connect(self.handle_mode_change)
        thermo.signal_cool_sp_change.connect(self.handle_cool_sp_change)
        thermo.signal_heat_sp_change.connect(self.handle_heat_sp_change)
        thermo.signal_ambient_humid_change.connect(
            self.handle_ambient_humid_change)
        thermo.signal_status_change.connect(self.handle_status_change)
        thermo.signal_hold_change.connect(self.handle_hold_change)
        thermo.signal_energy_change.connect(self.handle_energy_change)

        # Lightly test pairing and I mean light.  Most of this testing is
        # handled by other tests
        thermo.pair()
        msg = Msg.OutStandard.direct(addr, 0x19, 0x00)
        test_msg = protocol.msgs.pop(0)
        assert test_msg.to_bytes() == msg.to_bytes()

        # test get_status
        thermo.get_status()
        msg = Msg.OutExtended.direct(addr, 0x2e, 0x02,
                                     bytes([0x00] * 14), crc_type="CRC")
        test_msg = protocol.msgs.pop(0)
        assert test_msg.to_bytes() == msg.to_bytes()

        # test handling of get_status response CELSIUS
        flags = Msg.Flags(Msg.Flags.Type.DIRECT, True)
        msg = Msg.InpExtended(addr, addr, flags, 0x2e, 0x02,
                              bytes([0x01, 0x04, 0x0a, 0x21, 0x05, 0x11, 0x1b,
                                     0x1e, 0x00, 0xe0, 0x88, 0x0e, 0x0f,
                                     0xde]))
        thermo.handle_status(msg, on_done=self.done)
        assert self.status == Thermo.Status.OFF
        assert self.hold is False
        assert self.energy is False
        assert self.fan == Thermo.Fan.ON
        assert self.mode == Thermo.Mode.AUTO
        assert self.humid == 30
        assert self.cool_sp == 27
        assert self.heat_sp == 14
        assert self.ambient == 22.4
        assert thermo.units == Thermo.CELSIUS

        # Test FARENHEIT
        flags = Msg.Flags(Msg.Flags.Type.DIRECT, True)
        msg = Msg.InpExtended(addr, addr, flags, 0x2e, 0x02,
                              bytes([0x01, 0x04, 0x0a, 0x21, 0x05, 0x11, 0x50,
                                     0x1e, 0x00, 0xe0, 0x80, 0x39, 0x0f,
                                     0xde]))
        thermo.handle_status(msg, on_done=self.done)
        assert round(self.cool_sp, 0) == 27
        assert round(self.heat_sp, 0) == 14
        assert self.ambient, 1 == 22.4
        assert thermo.units == Thermo.FARENHEIT

        # Test cooling w/ hold
        flags = Msg.Flags(Msg.Flags.Type.DIRECT, True)
        msg = Msg.InpExtended(addr, addr, flags, 0x2e, 0x02,
                              bytes([0x01, 0x04, 0x0a, 0x21, 0x05, 0x11, 0x50,
                                     0x1e, 0x00, 0xe0, 0x91, 0x39, 0x0f,
                                     0xde]))
        thermo.handle_status(msg, on_done=self.done)
        assert self.status == Thermo.Status.COOLING
        assert self.hold is True

        # Test heating w/ energy
        flags = Msg.Flags(Msg.Flags.Type.DIRECT, True)
        msg = Msg.InpExtended(addr, addr, flags, 0x2e, 0x02,
                              bytes([0x01, 0x04, 0x0a, 0x21, 0x05, 0x11, 0x50,
                                     0x1e, 0x00, 0xe0, 0x86, 0x39, 0x0f,
                                     0xde]))
        thermo.handle_status(msg, on_done=self.done)
        assert self.status == Thermo.Status.HEATING
        assert self.energy is True

        # Test bad status response
        flags = Msg.Flags(Msg.Flags.Type.DIRECT, True)
        msg = Msg.InpExtended(addr, addr, flags, 0x2e, 0x02,
                              bytes([0x01, 0x04, 0x0a, 0x21, 0x05, 0xFF, 0x1b,
                                     0x1e, 0x00, 0xe0, 0x88, 0x0e, 0x0f,
                                     0xde]))
        thermo.handle_status(msg, on_done=self.done)

        # force a bad fan command, currently no way for this to happen
        # in the code, so just fake it here
        thermo.set_fan_mode_state(2)
        assert self.fan == Thermo.Fan.ON

        # test humidity setpoints, not enabled in code yet so this is just a
        # shell
        msg = Msg.OutExtended.direct(addr, 0x2e, 0x00,
                                     bytes([0x00] * 2 + [0x01] + [0x00] * 11),
                                     crc_type="CRC")
        thermo.get_humidity_setpoints()
        assert msg.to_bytes() == protocol.msgs.pop(0).to_bytes()
        thermo.handle_humidity_setpoints(msg)

        # Test enabling broadcast messages
        msg = Msg.OutExtended.direct(addr, 0x2e, 0x00,
                                     bytes([0x00] + [0x08] + [0x00] * 12))
        thermo.enable_broadcast()
        assert msg.to_bytes() == protocol.msgs.pop(0).to_bytes()

        thermo.handle_generic_ack(msg, on_done=self.done)

        # test thermo broadcast Messages
        flags = Msg.Flags(Msg.Flags.Type.ALL_LINK_BROADCAST, False)
        cool = IM.Address(0x00, 0x00, 0x01)
        msg = Msg.InpStandard(addr, cool, flags, 0x11, 0x00)
        thermo.handle_broadcast(msg)
        assert self.status == Thermo.Status.COOLING
        msg = Msg.InpStandard(addr, cool, flags, 0x13, 0x00)
        thermo.handle_broadcast(msg)
        assert self.status == Thermo.Status.OFF
        # test of bad group, shouldn't change status
        cool = IM.Address(0x00, 0x00, 0x07)
        msg = Msg.InpStandard(addr, cool, flags, 0x11, 0x00)
        thermo.handle_broadcast(msg)
        assert self.status == Thermo.Status.OFF
        # Test non-thermo broadcast
        cool = IM.Address(0x00, 0x00, 0x01)
        msg = Msg.InpStandard(addr, cool, flags, 0x20, 0x00)
        thermo.handle_broadcast(msg)

        # Test mode command
        msg = Msg.OutExtended.direct(addr, 0x6b, thermo.ModeCommands(0x04),
                                     bytes([0x00] * 14))
        thermo.mode_command(thermo.ModeCommands.HEAT)
        assert msg.to_bytes() == protocol.msgs.pop(0).to_bytes()

        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x6b,
                              thermo.ModeCommands.HEAT.value)
        thermo.handle_mode_command(msg, on_done=self.done)
        assert self.mode == thermo.ModeCommands.HEAT
        # Test bad ack
        msg = Msg.InpStandard(addr, addr, flags, 0x6c,
                              thermo.ModeCommands.HEAT.value)
        thermo.handle_mode_command(msg, on_done=self.done)
        assert self.mode == thermo.ModeCommands.HEAT

        # Test fan command
        msg = Msg.OutExtended.direct(addr, 0x6b, thermo.FanCommands(0x07),
                                     bytes([0x00] * 14))
        thermo.fan_command(thermo.FanCommands.ON)
        assert msg.to_bytes() == protocol.msgs.pop(0).to_bytes()

        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x6b,
                              thermo.FanCommands.ON.value)
        thermo.handle_fan_command(msg, on_done=self.done)
        assert self.fan == thermo.FanCommands.ON
        # Test bad ack
        msg = Msg.InpStandard(addr, addr, flags, 0x6c,
                              thermo.FanCommands.ON.value)
        thermo.handle_fan_command(msg, on_done=self.done)
        assert self.fan == thermo.FanCommands.ON

        # test heat setpoint command CELSIUS
        thermo.units = thermo.CELSIUS
        temp = 25
        msg = Msg.OutExtended.direct(addr, 0x6d, int(temp * 2),
                                     bytes([0x00] * 14))
        thermo.heat_sp_command(temp)
        assert msg.to_bytes() == protocol.msgs.pop(0).to_bytes()

        # test response handler
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x6d,
                              int(temp * 2))
        thermo.handle_heat_sp_command(msg, on_done=self.done)
        assert self.heat_sp == temp

        # Test FARENHEIT
        thermo.units = thermo.FARENHEIT
        temp_c = 25
        temp = (temp_c * 9 / 5) + 32
        msg = Msg.OutExtended.direct(addr, 0x6d, int(temp * 2),
                                     bytes([0x00] * 14))
        thermo.heat_sp_command(temp_c)
        assert msg.to_bytes() == protocol.msgs.pop(0).to_bytes()

        # test response handler
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x6d,
                              int(temp * 2))
        thermo.handle_heat_sp_command(msg, on_done=self.done)
        assert self.heat_sp == temp_c

        # BAd Ack
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x6a,
                              int(temp * 2))
        thermo.handle_heat_sp_command(msg, on_done=self.done)
        assert self.heat_sp == temp_c

        # test cool setpoint command CELSIUS
        thermo.units = thermo.CELSIUS
        temp = 25
        msg = Msg.OutExtended.direct(addr, 0x6c, int(temp * 2),
                                     bytes([0x00] * 14))
        thermo.cool_sp_command(temp)
        assert msg.to_bytes() == protocol.msgs.pop(0).to_bytes()

        # test response handler
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x6c,
                              int(temp * 2))
        thermo.handle_cool_sp_command(msg, on_done=self.done)
        assert self.cool_sp == temp

        # Test FARENHEIT
        thermo.units = thermo.FARENHEIT
        temp_c = 25
        temp = (temp_c * 9 / 5) + 32
        msg = Msg.OutExtended.direct(addr, 0x6c, int(temp * 2),
                                     bytes([0x00] * 14))
        thermo.cool_sp_command(temp_c)
        assert msg.to_bytes() == protocol.msgs.pop(0).to_bytes()

        # test response handler
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x6c,
                              int(temp * 2))
        thermo.handle_cool_sp_command(msg, on_done=self.done)
        assert self.cool_sp == temp_c

        # bad ack
        flags = Msg.Flags(Msg.Flags.Type.DIRECT_ACK, False)
        msg = Msg.InpStandard(addr, addr, flags, 0x6a,
                              int(temp * 2))
        thermo.handle_cool_sp_command(msg, on_done=self.done)
        assert self.cool_sp == temp_c

    def done(self, *args, **kwargs):
        pass

    #-----------------------------------------------------------------------
    def handle_ambient_temp_change(self, device, temp_c):
        self.ambient = temp_c

    #-----------------------------------------------------------------------
    def handle_fan_mode_change(self, device, fan_mode):
        self.fan = fan_mode

    #-----------------------------------------------------------------------
    def handle_mode_change(self, device, mode):
        self.mode = mode

    #-----------------------------------------------------------------------
    def handle_cool_sp_change(self, device, temp_c):
        self.cool_sp = temp_c

    #-----------------------------------------------------------------------
    def handle_heat_sp_change(self, device, temp_c):
        self.heat_sp = temp_c

    #-----------------------------------------------------------------------
    def handle_ambient_humid_change(self, device, humid):
        self.humid = humid

    #-----------------------------------------------------------------------
    def handle_status_change(self, device, status):
        self.status = status

    #-----------------------------------------------------------------------
    def handle_hold_change(self, device, hold):
        self.hold = hold

    #-----------------------------------------------------------------------
    def handle_energy_change(self, device, energy):
        self.energy = energy


class MockModem:
    def __init__(self, path):
        self.save_path = str(path)
        self.addr = IM.Address(0x0A, 0x0B, 0x0C)


class MockProto:
    def __init__(self):
        self.msgs = []

    def add_handler(self, *args):
        pass

    def send(self, msg, msg_handler, high_priority=False, after=None):
        self.msgs.append(msg)
