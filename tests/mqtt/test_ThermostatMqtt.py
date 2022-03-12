#===========================================================================
#
# Tests for: insteont_mqtt/mqtt/Thermostat.py
#
# pylint: disable=protected-access, too-many-statements
#===========================================================================
import enum
import pytest
import helpers as H
import insteon_mqtt as IM
from insteon_mqtt.Signal import Signal
from insteon_mqtt.mqtt.MsgTemplate import MsgTemplate


@pytest.fixture
def setup(mock_paho_mqtt, tmpdir):
    proto = H.main.MockProtocol()
    modem = H.main.MockModem(tmpdir)
    addr = IM.Address(1, 2, 3)
    name = "device name"
    dev = IM.device.Thermostat(proto, modem, addr, name, None)

    link = IM.network.Mqtt()
    mqttModem = H.mqtt.MockModem()
    mqtt = IM.mqtt.Mqtt(link, mqttModem)
    mdev = IM.mqtt.Thermostat(mqtt, dev)

    return H.Data(addr=addr, name=name, dev=dev, mdev=mdev, link=link,
                  proto=proto)

class Test_ThermostatMqtt:
    def test_basic(self):
        mqtt = MockMqtt()
        device = MockDevice()
        thermo = IM.mqtt.Thermostat(mqtt, device)

        #Ambient temperature
        device.signal_ambient_temp_change.emit(device, 22)
        assert mqtt.last_topic == 'insteon/01.02.03/ambient_temp'
        assert mqtt.last_payload == '{"temp_f" : 71.6, "temp_c" : 22}'

        # Fan mode
        device.signal_fan_mode_change.emit(device, device.Fan.AUTO)
        assert mqtt.last_topic == 'insteon/01.02.03/fan_state'
        assert mqtt.last_payload == 'auto'

        # Mode change
        device.signal_mode_change.emit(device, device.ModeCommands.AUTO)
        assert mqtt.last_topic == 'insteon/01.02.03/mode_state'
        assert mqtt.last_payload == 'auto'

        # Cool setpoint
        device.signal_cool_sp_change.emit(device, 22)
        assert mqtt.last_topic == 'insteon/01.02.03/cool_sp_state'
        assert mqtt.last_payload == '{"temp_f" : 71.6, "temp_c" : 22}'

        # heat setpoint
        device.signal_heat_sp_change.emit(device, 24)
        assert mqtt.last_topic == 'insteon/01.02.03/heat_sp_state'
        assert mqtt.last_payload == '{"temp_f" : 75.2, "temp_c" : 24}'

        # Humid Change
        device.signal_ambient_humid_change.emit(device, 50)
        assert mqtt.last_topic == 'insteon/01.02.03/humid_state'
        assert mqtt.last_payload == '50'

        # Status modify default payload to see all values
        thermo.status_state = MsgTemplate(
            topic='insteon/{{address}}/status_state',
            payload=('{"status": "{{status}}", "is_heating": {{is_heating}}, '
                     '"is_cooling": {{is_cooling}}}'))
        # Test cooling
        device.signal_status_change.emit(device, device.Status.COOLING)
        assert mqtt.last_topic == 'insteon/01.02.03/status_state'
        assert mqtt.last_payload == ('{"status": "cooling", "is_heating": 0, '
                                     '"is_cooling": 1}')
        # Test heating
        device.signal_status_change.emit(device, device.Status.HEATING)
        assert mqtt.last_topic == 'insteon/01.02.03/status_state'
        assert mqtt.last_payload == ('{"status": "heating", "is_heating": 1, '
                                     '"is_cooling": 0}')

        # hold modify default payload to see all values
        thermo.hold_state = MsgTemplate(
            topic='insteon/{{address}}/hold_state',
            payload='{"hold": "{{hold_str}}", "is_hold": {{is_hold}}}')
        # Test no hold
        device.signal_hold_change.emit(device, False)
        assert mqtt.last_topic == 'insteon/01.02.03/hold_state'
        assert mqtt.last_payload == '{"hold": "off", "is_hold": 0}'
        # Test hold
        device.signal_hold_change.emit(device, True)
        assert mqtt.last_topic == 'insteon/01.02.03/hold_state'
        assert mqtt.last_payload == '{"hold": "temp", "is_hold": 1}'

        # energy modify default payload to see all values
        thermo.energy_state = MsgTemplate(
            topic='insteon/{{address}}/energy_state',
            payload='{"energy": "{{energy_str}}", "is_energy": {{is_energy}}}')
        # Test no energy
        device.signal_energy_change.emit(device, False)
        assert mqtt.last_topic == 'insteon/01.02.03/energy_state'
        assert mqtt.last_payload == '{"energy": "off", "is_energy": 0}'
        # Test energy
        device.signal_energy_change.emit(device, True)
        assert mqtt.last_topic == 'insteon/01.02.03/energy_state'
        assert mqtt.last_payload == '{"energy": "on", "is_energy": 1}'

        # Test commands
        # test mode
        message = MockMessage(
            topic='insteon/01.02.03/mode_command',
            payload='auto',
            )
        thermo._input_mode(None, None, message)
        assert device.mode == device.ModeCommands.AUTO

        # test fan
        message = MockMessage(
            topic='insteon/01.02.03/fan_command',
            payload='on',
            )
        thermo._input_fan(None, None, message)
        assert device.fan == device.FanCommands.ON

        # test heat sp
        # sent in F
        message = MockMessage(
            topic='insteon/01.02.03/heat_sp_command',
            payload='80',
            )
        thermo._input_heat_setpoint(None, None, message)
        assert round(device.heat_sp, 1) == 26.7

        # temp sent in C
        thermo.heat_sp_command = MsgTemplate(
            topic='insteon/{{address}}/heat_sp_command',
            payload='{ "temp_c" : {{value}} }')
        message = MockMessage(
            topic='insteon/01.02.03/heat_sp_command',
            payload='26.6666',
            )
        thermo._input_heat_setpoint(None, None, message)
        assert round(device.heat_sp, 1) == 26.7

        # temp sent in both should default to F
        thermo.heat_sp_command = MsgTemplate(
            topic='insteon/{{address}}/heat_sp_command',
            payload=('{ "temp_c" : {{json.temp_c}}, '
                     '"temp_f" : {{json.temp_f}} }'),
            )
        message = MockMessage(
            topic='insteon/01.02.03/heat_sp_command',
            payload='{"temp_f": 80, "temp_c": 30}',
            )
        thermo._input_heat_setpoint(None, None, message)
        assert round(device.heat_sp, 1) == 30

        # test cool sp
        # sent in F
        message = MockMessage(
            topic='insteon/01.02.03/cool_sp_command',
            payload='80',
            )
        thermo._input_cool_setpoint(None, None, message)
        assert round(device.cool_sp, 1) == 26.7

        # temp sent in C
        thermo.cool_sp_command = MsgTemplate(
            topic='insteon/{{address}}/cool_sp_command',
            payload='{ "temp_c" : {{value}} }')
        message = MockMessage(
            topic='insteon/01.02.03/cool_sp_command',
            payload='26.6666',
            )
        thermo._input_cool_setpoint(None, None, message)
        assert round(device.cool_sp, 1) == 26.7

        # temp sent in both should default to F
        thermo.cool_sp_command = MsgTemplate(
            topic='insteon/{{address}}/cool_sp_command',
            payload=('{ "temp_c" : {{json.temp_c}}, '
                     '"temp_f" : {{json.temp_f}} }'),
            )
        message = MockMessage(
            topic='insteon/01.02.03/cool_sp_command',
            payload='{"temp_f": 80, "temp_c": 30}',
            )
        thermo._input_cool_setpoint(None, None, message)
        assert round(device.cool_sp, 1) == 30

    #-----------------------------------------------------------------------
    def test_discovery(self, setup):
        mdev, dev, link = setup.getAll(['mdev', 'dev', 'link'])
        topic = "insteon/%s" % setup.addr.hex

        mdev.load_config({"thermostat": {"junk": "junk"}})
        assert mdev.default_discovery_cls == "thermostat"
        assert mdev.rendered_topic_map == {
            'ambient_temp_topic': 'insteon/01.02.03/ambient_temp',
            'cool_sp_command_topic': 'insteon/01.02.03/cool_sp_command',
            'cool_sp_state_topic': 'insteon/01.02.03/cool_sp_state',
            'energy_state_topic': 'insteon/01.02.03/energy_state',
            'fan_command_topic': 'insteon/01.02.03/fan_command',
            'fan_state_topic': 'insteon/01.02.03/fan_state',
            'heat_sp_command_topic': 'insteon/01.02.03/heat_sp_command',
            'heat_sp_state_topic': 'insteon/01.02.03/heat_sp_state',
            'hold_state_topic': 'insteon/01.02.03/hold_state',
            'humid_state_topic': 'insteon/01.02.03/humid_state',
            'mode_command_topic': 'insteon/01.02.03/mode_command',
            'mode_state_topic': 'insteon/01.02.03/mode_state',
            'status_state_topic': 'insteon/01.02.03/status_state'
        }
        assert len(mdev.extra_topic_nums) == 0

#===========================================================================
class MockMqtt:
    def __init__(self):
        self.last_payload = None
        self.last_topic = None
        self.mode_command = None
        self.device_info_template = {}

    def publish(self, topic, payload, qos=None, retain=None):
        self.last_topic = topic
        self.last_payload = payload


#===========================================================================
class MockDevice:
    # mock thermostat device
    FARENHEIT = 0
    CELSIUS = 1

    class ModeCommands(enum.IntEnum):
        OFF = 0x09
        HEAT = 0x04
        COOL = 0x05
        AUTO = 0x06
        PROGRAM = 0x0a

    class Fan(enum.IntEnum):
        AUTO = 0x00
        ON = 0x01

    class FanCommands(enum.IntEnum):
        ON = 0x07
        AUTO = 0x08

    class Status(enum.Enum):
        OFF = "OFF"
        HEATING = "HEATING"
        COOLING = "COOLING"

    def __init__(self):
        self.addr = IM.Address(0x01, 0x02, 0x03)
        self.name = "mock_thermo"
        self.label = "mock_thermo"
        self.mode = None
        self.fan = None
        self.heat_sp = None
        self.cool_sp = None
        self.units = MockDevice.FARENHEIT
        self.signal_ambient_temp_change = Signal()  # emit(device, Int temp_c)
        self.signal_fan_mode_change = Signal()  # emit(device, Fan fan mode)
        self.signal_mode_change = Signal()  # emit(device, Mode mode)
        self.signal_cool_sp_change = Signal()  # emit(device, Int cool_sp in c)
        self.signal_heat_sp_change = Signal()  # emit(device, Int heat_sp in c)
        self.signal_ambient_humid_change = Signal()  # emit(device, Int humid)
        self.signal_status_change = Signal()  # emit(device, Str status)
        self.signal_hold_change = Signal()  # emit(device, bool)
        self.signal_energy_change = Signal()   # emit(device, bool)

    def mode_command(self, mode_member):
        self.mode = mode_member

    def fan_command(self, mode_member):
        self.fan = mode_member

    def heat_sp_command(self, mode_member):
        self.heat_sp = mode_member

    def cool_sp_command(self, mode_member):
        self.cool_sp = mode_member


#===========================================================================
class MockMessage:
    # A mock versio of a paho mqtt message
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = payload.encode('utf-8')
