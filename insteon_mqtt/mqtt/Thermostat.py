#===========================================================================
#
# MQTT thermostat sensor device
#
#===========================================================================
from .. import log
from .MsgTemplate import MsgTemplate

LOG = log.get_logger()


class Thermostat:
    """MQTT interface to an Insteon thermostat switch.

    This class connects to a device.Thermostat and converts it's output
    state changes to MQTT messages.  It also subscribes to topics to allow
    input MQTT messages to change the state of the Insteon device.
    """
    def __init__(self, mqtt, device):
        """Constructor

        Args:
          mqtt (mqtt.Mqtt):  The MQTT main interface.
          device (device.Thermostat):  The Insteon object to link to.
        """
        self.mqtt = mqtt
        self.device = device

        # Set up the default templates for the MQTT messages and payloads.
        # Templates for states
        self.ambient_temp = MsgTemplate(
            topic='insteon/{{address}}/ambient_temp',
            payload='{"temp_f" : {{temp_f}}, "temp_c" : {{temp_c}}}')
        self.fan_state = MsgTemplate(
            topic='insteon/{{address}}/fan_state',
            payload='{{fan_mode}}')
        self.mode_state = MsgTemplate(
            topic='insteon/{{address}}/mode_state',
            payload='{{mode}}')
        self.cool_sp_state = MsgTemplate(
            topic='insteon/{{address}}/cool_sp_state',
            payload='{"temp_f" : {{temp_f}}, "temp_c" : {{temp_c}}}')
        self.heat_sp_state = MsgTemplate(
            topic='insteon/{{address}}/heat_sp_state',
            payload='{"temp_f" : {{temp_f}}, "temp_c" : {{temp_c}}}')
        self.humid_state = MsgTemplate(
            topic='insteon/{{address}}/humid_state',
            payload='{{humid}}')
        self.status_state = MsgTemplate(
            topic='insteon/{{address}}/status_state',
            payload='{{status}}')
        self.hold_state = MsgTemplate(
            topic='insteon/{{address}}/hold_state',
            payload='{{hold_str}}')
        self.energy_state = MsgTemplate(
            topic='insteon/{{address}}/energy_state',
            payload='{{energy_str}}')

        # Templates for Commands
        self.mode_command = MsgTemplate(
            topic='insteon/{{address}}/mode_command',
            payload='{ "cmd" : "{{value.lower()}}" }')
        self.fan_command = MsgTemplate(
            topic='insteon/{{address}}/fan_command',
            payload='{ "cmd" : "{{value.lower()}}" }')
        self.heat_sp_command = MsgTemplate(
            topic='insteon/{{address}}/heat_sp_command',
            payload='{ "temp_f" : {{value}} }')
        self.cool_sp_command = MsgTemplate(
            topic='insteon/{{address}}/cool_sp_command',
            payload='{ "temp_f" : {{value}} }')

        # Receive notifications from the Insteon device when it changes.
        device.signal_ambient_temp_change.connect(
            self._insteon_ambient_temp_change)
        device.signal_fan_mode_change.connect(self._insteon_fan_mode_change)
        device.signal_mode_change.connect(self._insteon_mode_change)
        device.signal_cool_sp_change.connect(self._insteon_cool_sp_change)
        device.signal_heat_sp_change.connect(self._insteon_heat_sp_change)
        device.signal_ambient_humid_change.connect(
            self._insteon_ambient_humid_change)
        device.signal_status_change.connect(self._insteon_status_change)
        device.signal_hold_change.connect(self._insteon_hold_change)
        device.signal_energy_change.connect(self._insteon_energy_change)

    #-----------------------------------------------------------------------
    def load_config(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict:  The configuration dictionary to load from.  The object
                 config is stored in config['thermostat'].
          qos (int):  The default quality of service level to use.
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

        Subscriptions are used when the object has things that can be
        commanded to change.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
          qos (int):  The quality of service to use.
        """
        topic = self.mode_command.render_topic(self.template_data())
        link.subscribe(topic, qos, self._input_mode)

        topic = self.fan_command.render_topic(self.template_data())
        link.subscribe(topic, qos, self._input_fan)

        topic = self.heat_sp_command.render_topic(self.template_data())
        link.subscribe(topic, qos, self._input_heat_setpoint)

        topic = self.cool_sp_command.render_topic(self.template_data())
        link.subscribe(topic, qos, self._input_cool_setpoint)

    #-----------------------------------------------------------------------
    def unsubscribe(self, link):
        """Unsubscribe to any MQTT topics the object was subscribed to.

        Args:
          link (network.Mqtt):  The MQTT network client to use.
        """
        topic = self.mode_command.render_topic(self.template_data())
        link.unsubscribe(topic)

        topic = self.fan_command.render_topic(self.template_data())
        link.unsubscribe(topic)

        topic = self.heat_sp_command.render_topic(self.template_data())
        link.unsubscribe(topic)

        topic = self.cool_sp_command.render_topic(self.template_data())
        link.unsubscribe(topic)

    #-----------------------------------------------------------------------
    def template_data(self):
        """Create the Jinja templating data variables for on/off messages.

        Returns:
          dict:  Returns a dict with the variables available for templating.
        """
        data = {
            "address" : self.device.addr.hex,
            "name" : self.device.name if self.device.name
                     else self.device.addr.hex
            }

        return data

    #-----------------------------------------------------------------------
    def _insteon_ambient_temp_change(self, device, temp_c):
        """Posts to mqtt changes in ambient temperature

        This is triggered via signal when the ambient temp changes.

        Args:
          device (device.Thermostat):  The Insteon device that changed.
          temp_c (float):  The temp in Celsius.
        """
        LOG.info("MQTT received temp change %s = %s C", device.label,
                 temp_c)

        # Set up the variables that can be used in the templates.
        data = self.template_data()
        data["temp_c"] = temp_c
        data["temp_f"] = round((temp_c * 9) / 5 + 32, 1)

        self.ambient_temp.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def _insteon_fan_mode_change(self, device, fan_mode):
        """Posts to mqtt changes in fan mode

        This is triggered via signal when the fan mode change.

        Args:
          device (device.Thermostat):  The Insteon device that changed.
          fan_mode (Thermostat.Fan): The fan state.
        """
        LOG.info("MQTT received fan mode change %s = %s C", device.label,
                 fan_mode)

        # Set up the variables that can be used in the templates.
        data = self.template_data()
        data["fan_mode"] = fan_mode.name.lower()
        data["is_fan_on"] = 1 if fan_mode == fan_mode.ON else 0

        self.fan_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def _insteon_mode_change(self, device, mode):
        """Posts to mqtt changes in the hvac mode

        This is triggered via signal when the mode changes.

        Args:
          device (device.Thermostat):  The Insteon device that changed.
          mode (Thermostat.Mode) The mode state.
        """
        LOG.info("MQTT received mode change %s = %s C", device.label, mode)

        # Set up the variables that can be used in the templates.
        data = self.template_data()
        data["mode"] = mode.name.lower()

        self.mode_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def _insteon_cool_sp_change(self, device, temp_c):
        """Posts to mqtt when the cool setpoint changes

        This is triggered via signal when the cool setpoint changes.

        Args:
          device (device.Thermostat):  The Insteon device that changed.
          temp_c (flaot): The temp in Celsius.
        """
        LOG.info("MQTT received cool setpoint change %s = %s", device.label,
                 temp_c)

        # Set up the variables that can be used in the templates.
        data = self.template_data()
        data["temp_c"] = round(temp_c, 1)
        data["temp_f"] = round((temp_c * 9) / 5 + 32, 1)

        self.cool_sp_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def _insteon_heat_sp_change(self, device, temp_c):
        """Posts to mqtt changes in the heat setpoint

        This is triggered via signal when the heat setpoint changes.

        Args:
          device (device.Thermostat):  The Insteon device that changed.
          temp_c (float): The temp in Celsius.
        """
        LOG.info("MQTT received heat setpoint change %s = %s", device.label,
                 temp_c)

        # Set up the variables that can be used in the templates.
        data = self.template_data()
        data["temp_c"] = round(temp_c, 1)
        data["temp_f"] = round((temp_c * 9) / 5 + 32, 1)

        self.heat_sp_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def _insteon_ambient_humid_change(self, device, humidity):
        """Posts to mqtt changes in the ambient humidity

        This is triggered via signal when the ambient humidity changes.

        Args:
          device (device.Thermostat):  The Insteon device that changed.
          humidity (int): The humidity percentage.
        """
        LOG.info("MQTT received humidity change %s = %s", device.label,
                 humidity)

        # Set up the variables that can be used in the templates.
        data = self.template_data()
        data["humid"] = humidity

        self.humid_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def _insteon_status_change(self, device, status):
        """Posts to mqtt changes in the hvac status

        This is triggered via signal when the hvac status changes.

        Args:
          device (device.Thermostat):  The Insteon device that changed.
          status (Thermostat.Stuats): The current operation status.
        """
        LOG.info("MQTT received status change %s = %s", device.label,
                 status.value)

        data = self.template_data()
        data["status"] = status.name.lower()
        data["is_heating"] = 1 if status == status.HEATING else 0
        data["is_cooling"] = 1 if status == status.COOLING else 0

        self.status_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def _insteon_hold_change(self, device, hold):
        """Posts to mqtt changes in the hold status

        This is triggered via signal when the hold status changes.

        Args:
          device (device.Thermostat):  The Insteon device that changed.
          hold (bool):  The hold Status
        """
        LOG.info("MQTT received hold change %s = %s", device.label, hold)

        # Set up the variables that can be used in the templates.
        data = self.template_data()
        data["hold_str"] = "temp" if hold else "off"
        data["is_hold"] = 1 if hold else 0

        self.hold_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def _insteon_energy_change(self, device, energy):
        """Posts to mqtt changes in the energy status

        This is triggered via signal when the energy status changes.

        Args:
          device (device.Thermostat):  The Insteon device that changed.
          energy (bool): Energy Status
        """
        LOG.info("MQTT received energy change %s = %s", device.label, energy)

        data = self.template_data()
        data["energy_str"] = "on" if energy else "off"
        data["is_energy"] = 1 if energy else 0

        self.energy_state.publish(self.mqtt, data)

    #-----------------------------------------------------------------------
    def _input_mode(self, client, data, message):
        """Handle an input mode change MQTT message.

        This is called when we receive a message on the mode change MQTT
        topic subscription.  Parse the message and pass the command to the
        Insteon device.

        Options are [off, auto, heat, cool, program]

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.info("Thermostat message %s %s", message.topic, message.payload)

        data = self.mode_command.to_json(message.payload)
        if not data:
            return

        LOG.info("Thermostat mode command: %s", data)
        try:
            # Convert the input string to the enum value.
            mode_str = data['cmd'].upper()
            mode = self.device.ModeCommands[mode_str]
            self.device.mode_command(mode)
        except:
            LOG.exception("Invalid thermostat mode command: %s", data)

    #-----------------------------------------------------------------------
    def _input_fan(self, client, data, message):
        """Handle an input mode change MQTT message.

        This is called when we receive a message on the mode change MQTT
        topic subscription.  Parse the message and pass the command to the
        Insteon device.

        Options are [on, auto]

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.info("Thermostat message %s %s", message.topic, message.payload)

        data = self.fan_command.to_json(message.payload)
        if not data:
            return

        LOG.info("Thermostat fan mode command: %s", data)
        try:
            # Convert the input string to the enum value.
            mode_str = data['cmd'].upper()
            mode = self.device.FanCommands[mode_str]
            self.device.fan_command(mode)
        except:
            LOG.exception("Unknown thermostat fan mode command: %s", data)

    #-----------------------------------------------------------------------
    def _input_heat_setpoint(self, client, data, message):
        """Handle an input mode change MQTT message.

        This is called when we receive a message on the mode change MQTT
        topic subscription.  Parse the message and pass the command to the
        Insteon device.

        Value should be in the form of:
          { temp_f: float } or { temp_c: float}
        If temp_c is present, it will be used, regardless of if temp_f is also
        present.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.info("Thermostat message %s %s", message.topic, message.payload)

        data = self.heat_sp_command.to_json(message.payload)
        if not data:
            return

        LOG.info("Thermostat heat setpoint command: %s", data)
        try:
            temp_c = data.get('temp_c', None)
            if temp_c is None:
                temp_c = (data['temp_f'] - 32) * 5 / 9

            self.device.heat_sp_command(temp_c)
        except:
            LOG.exception("Invalid thermostat heat setpoint command: %s", data)

    #-----------------------------------------------------------------------
    def _input_cool_setpoint(self, client, data, message):
        """Handle an input cooling setpoint change MQTT message.

        This is called when we receive a message on the cooling setpoint
        change MQTT topic subscription.  Parse the message and pass the
        command to the Insteon device.

        Value should be in the form of:
          { temp_f: float } or { temp_c: float}
        If temp_c is present, it will be used, regardless of if temp_f is also
        present.

        Args:
          client (paho.Client):  The paho mqtt client (self.link).
          data:  Optional user data (unused).
          message:  MQTT message - has attrs: topic, payload, qos, retain.
        """
        LOG.info("Thermostat message %s %s", message.topic, message.payload)

        data = self.cool_sp_command.to_json(message.payload)
        if not data:
            return

        LOG.info("Thermostat cool setpoint command: %s", data)
        try:
            temp_c = data.get('temp_c', None)
            if temp_c is None:
                temp_c = (data['temp_f'] - 32) * 5 / 9

            self.device.cool_sp_command(temp_c)
        except:
            LOG.exception("Invalid thermostat cool setpoint command: %s", data)
