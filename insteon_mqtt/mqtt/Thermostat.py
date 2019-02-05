#===========================================================================
#
# MQTT thermostat sensor device
#
#===========================================================================
from .. import log
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class Thermostat:
    """MQTT Thermostat object.

    This class links an Insteon Thermostat object to MQTT.  Any
    change in the Insteon device will trigger an MQTT message.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt:    (Mqtt) the main MQTT interface object.
          device:  The insteon thermostat device object.
        """
        self.mqtt = mqtt
        self.device = device

        # Set up the default templates for the MQTT messages and payloads.
        # Templates for states
        self.ambient_temp = MsgTemplate(
            topic='insteon/{{address}}/ambient_temp',
            payload='{"temp_f" : {{temp_f}}, "temp_c" : {{temp_c}}}',
            )
        self.fan_state = MsgTemplate(
            topic='insteon/{{address}}/fan_state',
            payload='{{fan_mode}}',
            )
        self.mode_state = MsgTemplate(
            topic='insteon/{{address}}/mode_state',
            payload='{{mode}}',
            )
        self.cool_sp_state = MsgTemplate(
            topic='insteon/{{address}}/cool_sp_state',
            payload='{"temp_f" : {{temp_f}}, "temp_c" : {{temp_c}}}',
            )
        self.heat_sp_state = MsgTemplate(
            topic='insteon/{{address}}/heat_sp_state',
            payload='{"temp_f" : {{temp_f}}, "temp_c" : {{temp_c}}}',
            )
        self.humid_state = MsgTemplate(
            topic='insteon/{{address}}/humid_state',
            payload='{{humid}}',
            )
        self.status_state = MsgTemplate(
            topic='insteon/{{address}}/status_state',
            payload='{{status}}',
            )
        self.hold_state = MsgTemplate(
            topic='insteon/{{address}}/hold_state',
            payload='{{hold_str}}',
            )
        self.energy_state = MsgTemplate(
            topic='insteon/{{address}}/energy_state',
            payload='{{energy_str}}',
            )

        # Templates for Commands
        self.mode_command = MsgTemplate(
            topic='insteon/{{address}}/mode_command',
            payload='{ "cmd" : "{{value.lower()}}" }',
            )
        self.fan_command = MsgTemplate(
            topic='insteon/{{address}}/fan_command',
            payload='{ "cmd" : "{{value.lower()}}" }',
            )
        self.heat_sp_command = MsgTemplate(
            topic='insteon/{{address}}/heat_sp_command',
            payload='{ "temp_f" : {{value}} }',
            )
        self.cool_sp_command = MsgTemplate(
            topic='insteon/{{address}}/cool_sp_command',
            payload='{ "temp_f" : {{value}} }',
            )

        # Receive notifications from the Insteon device when it changes.
        device.signal_ambient_temp_change.connect(
            self.handle_ambient_temp_change)
        device.signal_fan_mode_change.connect(self.handle_fan_mode_change)
        device.signal_mode_change.connect(self.handle_mode_change)
        device.signal_cool_sp_change.connect(self.handle_cool_sp_change)
        device.signal_heat_sp_change.connect(self.handle_heat_sp_change)
        device.signal_ambient_humid_change.connect(
            self.handle_ambient_humid_change)
        device.signal_status_change.connect(self.handle_status_change)
        device.signal_hold_change.connect(self.handle_hold_change)
        device.signal_energy_change.connect(self.handle_energy_change)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config:   The configuration dictionary to load from.  The object
                    config is stored in config['thermostat'].
          qos:      The default quality of service level to use.
        """
        data = config.get("thermostat", None)
        if not data:
            return

        # Update the MQTT topics and payloads from the config file.
        self.ambient_temp.load_config(data, 'ambient_temp_topic',
                                      'ambient_temp_payload', qos)
        self.fan_state.load_config(data, 'fan_state_topic',
                                   'fan_state_payload', qos)
        self.mode_state.load_config(data, 'mode_state_topic',
                                    'mode_state_payload', qos)
        self.cool_sp_state.load_config(data, 'cool_sp_state_topic',
                                       'cool_sp_state_payload', qos)
        self.heat_sp_state.load_config(data, 'heat_sp_state_topic',
                                       'heat_sp_state_payload', qos)
        self.humid_state.load_config(data, 'humid_state_topic',
                                     'humid_state_payload', qos)
        self.status_state.load_config(data, 'status_state_topic',
                                      'status_state_payload', qos)
        self.hold_state.load_config(data, 'hold_state_topic',
                                    'hold_state_payload', qos)
        self.energy_state.load_config(data, 'energy_state_topic',
                                      'energy_state_payload', qos)
        self.mode_command.load_config(config, 'mode_command_topic',
                                      'mode_command_payload', qos)
        self.fan_command.load_config(config, 'fan_command_topic',
                                     'fan_command_payload', qos)
        self.heat_sp_command.load_config(config, 'heat_sp_command_topic',
                                         'heat_sp_command_payload', qos)
        self.cool_sp_command.load_config(config, 'cool_sp_command_topic',
                                         'cool_sp_command_payload', qos)

    #-----------------------------------------------------------------------
    def subscribe(self, link, qos):
        """Subscribe to any MQTT topics the object needs.

        Args:
          link:   The MQTT network client to use.
          qos:    The quality of service to use.
        """
        topic = self.mode_command.render_topic(self.template_data())
        link.subscribe(topic, qos, self.handle_mode_command)

        topic = self.fan_command.render_topic(self.template_data())
        link.subscribe(topic, qos, self.handle_fan_command)

        topic = self.heat_sp_command.render_topic(self.template_data())
        link.subscribe(topic, qos, self.handle_heat_sp_command)

        topic = self.cool_sp_command.render_topic(self.template_data())
        link.subscribe(topic, qos, self.handle_cool_sp_command)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link:   The MQTT network client to use.
        """
        topic = self.mode_command.render_topic(self.template_data())
        self.mqtt.unsubscribe(topic)

        topic = self.fan_command.render_topic(self.template_data())
        self.mqtt.unsubscribe(topic)

        topic = self.heat_sp_command.render_topic(self.template_data())
        self.mqtt.unsubscribe(topic)

        topic = self.cool_sp_command.render_topic(self.template_data())
        self.mqtt.unsubscribe(topic)

    #-----------------------------------------------------------------------
    def template_data(self):
        """Provides the data common to all templates

        Returns:
          (str) A json string of the data.
        """
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex
            }

        return data

    #-----------------------------------------------------------------------
    def handle_ambient_temp_change(self, device, temp_c):
        """Posts to mqtt changes in ambient temperature

        This is triggered via signal when the ambient temp changes.

        Args:
          device:    (device.Base) The Insteon device that changed.
          temp_c:    the temp in Celsius.
        """
        LOG.info("MQTT received temp change %s = %s C", device.label,
                 temp_c)

        # Set up the variables that can be used in the templates.
        data = {
            "temp_c": temp_c,
            "temp_f": round((temp_c * 9) / 5 + 32, 1)
            }
        data.update(self.template_data())

        # Publish topic
        self.ambient_temp.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_fan_mode_change(self, device, fan_mode):
        """Posts to mqtt changes in fan mode

        This is triggered via signal when the fan mode change.

        Args:
          device:    (device.Base) The Insteon device that changed.
          fan_mode:  Thermostat.Fan state.
        """
        LOG.info("MQTT received fan mode change %s = %s C", device.label,
                 fan_mode)

        is_fan_on = 0
        if fan_mode.name == "on":
            is_fan_on = 1

        # Set up the variables that can be used in the templates.
        data = {
            "fan_mode": fan_mode.name.upper(),
            "is_fan_on": is_fan_on
            }
        data.update(self.template_data())

        # Publish topic
        self.fan_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_mode_change(self, device, mode):
        """Posts to mqtt changes in the hvac mode

        This is triggered via signal when the mode changes.

        Args:
          device:    (device.Base) The Insteon device that changed.
          mode:      Thermostat.Mode state.
        """
        LOG.info("MQTT received mode change %s = %s C", device.label,
                 mode)

        # Set up the variables that can be used in the templates.
        data = {
            "mode": mode.name.upper(),
            }
        data.update(self.template_data())

        # Publish topic
        self.mode_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_cool_sp_change(self, device, temp_c):
        """Posts to mqtt when the cool setpoint changes

        This is triggered via signal when the cool setpoint changes.

        Args:
          device:    (device.Base) The Insteon device that changed.
          temp_c:    the temp in Celsius.
        """
        LOG.info("MQTT received cool setpoint change %s = %s", device.label,
                 temp_c)

        # Set up the variables that can be used in the templates.
        data = {
            "temp_c": round(temp_c, 1),
            "temp_f": round((temp_c * 9) / 5 + 32, 1)
            }
        data.update(self.template_data())

        # Publish topic
        self.cool_sp_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_heat_sp_change(self, device, temp_c):
        """Posts to mqtt changes in the heat setpoint

        This is triggered via signal when the heat setpoint changes.

        Args:
          device:    (device.Base) The Insteon device that changed.
          temp_c:    the temp in Celsius.
        """
        LOG.info("MQTT received heat setpoint change %s = %s", device.label,
                 temp_c)

        # Set up the variables that can be used in the templates.
        data = {
            "temp_c": round(temp_c, 1),
            "temp_f": round((temp_c * 9) / 5 + 32, 1)
            }
        data.update(self.template_data())

        # Publish topic
        self.heat_sp_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_ambient_humid_change(self, device, humid):
        """Posts to mqtt changes in the ambient humidity

        This is triggered via signal when the ambient humidity changes.

        Args:
          device:    (device.Base) The Insteon device that changed.
          humid:     (int) the humidity percentage.
        """
        LOG.info("MQTT received humidity change %s = %s", device.label,
                 humid)

        # Set up the variables that can be used in the templates.
        data = {
            "humid": humid
            }
        data.update(self.template_data())

        # Publish topic
        self.humid_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_status_change(self, device, status):
        """Posts to mqtt changes in the hvac status

        This is triggered via signal when the hvac status changes.

        Args:
          device:    (device.Base) The Insteon device that changed.
          status:    (str)  OFF, HEATING, COOLING
        """
        status = status.upper()
        LOG.info("MQTT received status change %s = %s", device.label,
                 status)

        is_heating = is_cooling = 0
        if status == "HEATING":
            is_heating = 1
        elif status == "COOLING":
            is_cooling = 1

        # Set up the variables that can be used in the templates.
        data = {
            "status": status,
            "is_heating": is_heating,
            "is_cooling": is_cooling
            }
        data.update(self.template_data())

        # Publish topic
        self.status_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_hold_change(self, device, hold):
        """Posts to mqtt changes in the hold status

        This is triggered via signal when the hold status changes.

        Args:
          device:    (device.Base) The Insteon device that changed.
          hold:      (bool)  Hold Status
        """
        LOG.info("MQTT received hold change %s = %s", device.label,
                 hold)

        # Set up the variables that can be used in the templates.
        hold_str = "OFF"
        is_hold = 0
        if hold:
            hold_str = "TEMP"
            is_hold = 1
        data = {
            "hold_str": hold_str,
            "is_hold": is_hold
            }
        data.update(self.template_data())

        # Publish topic
        self.hold_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_energy_change(self, device, energy):
        """Posts to mqtt changes in the energy status

        This is triggered via signal when the energy status changes.

        Args:
          device:    (device.Base) The Insteon device that changed.
          energy:    (bool)  Energy Status
        """
        LOG.info("MQTT received energy change %s = %s", device.label,
                 energy)

        # Set up the variables that can be used in the templates.
        energy_str = "OFF"
        is_energy = 0
        if energy:
            energy_str = "ON"
            is_energy = 1
        data = {
            "energy_str": energy_str,
            "is_energy": is_energy
            }
        data.update(self.template_data())

        # Publish topic
        self.energy_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def handle_mode_command(self, client, data, message):
        """Command a change in the thermostat mode

        Options are [off, auto, heat, cool, program]

        """
        LOG.info("Thermostat message %s %s", message.topic, message.payload)

        data = self.mode_command.to_json(message.payload)
        if not data:
            return

        LOG.info("Thermostat mode command: %s", data)
        try:
            mode_member = self.device.ModeCommands[data['cmd']]
        except KeyError:
            LOG.exception("Unknown thermostat mode %s.", data['cmd'])
            return

        self.device.mode_command(mode_member)

    #-----------------------------------------------------------------------
    def handle_fan_command(self, client, data, message):
        """Command a change in the thermostat fan mode

        Options are [on, auto]

        """
        LOG.info("Thermostat message %s %s", message.topic, message.payload)

        data = self.fan_command.to_json(message.payload)
        if not data:
            return

        LOG.info("Thermostat fan mode command: %s", data)
        try:
            mode_member = self.device.FanCommands[data['cmd']]
        except KeyError:
            LOG.exception("Unknown thermostat fan mode %s.", data['cmd'])
            return

        self.device.fan_command(mode_member)

    #-----------------------------------------------------------------------
    def handle_heat_sp_command(self, client, data, message):
        """Command a change in the thermostat heat setpoint

        Value should be in the form of:
        { temp_f: float,
          temp_c: float}

        If temp_f is present, it will be used, regardless of if temp_c is also
        present

        """
        LOG.info("Thermostat message %s %s", message.topic, message.payload)

        data = self.heat_sp_command.to_json(message.payload)
        if not data:
            return

        LOG.info("Thermostat heat setpoint command: %s", data)
        if 'temp_f' in data:
            temp_c = (data['temp_f'] - 32) * 5 / 9
            self.device.heat_sp_command(temp_c)
        elif 'temp_c' in data:
            self.device.heat_sp_command(data['temp_c'])
        else:
            LOG.error("Unknown thermostat heat setpoint %s.", data)

    #-----------------------------------------------------------------------
    def handle_cool_sp_command(self, client, data, message):
        """Command a change in the thermostat cool setpoint

        Value should be in the form of:
        { temp_f: float,
          temp_c: float}

        If temp_f is present, it will be used, regardless of if temp_c is also
        present

        """
        LOG.info("Thermostat message %s %s", message.topic, message.payload)

        data = self.cool_sp_command.to_json(message.payload)
        if not data:
            return

        LOG.info("Thermostat cool setpoint command: %s", data)
        if 'temp_f' in data:
            temp_c = (data['temp_f'] - 32) * 5 / 9
            self.device.cool_sp_command(temp_c)
        elif 'temp_c' in data:
            self.device.cool_sp_command(data['temp_c'])
        else:
            LOG.error("Unknown thermostat cool setpoint %s.", data)
