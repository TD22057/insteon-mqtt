#===========================================================================
#
# MQTT Discovery Topic
#
#===========================================================================
import json
import jinja2
from ... import log
from ..MsgTemplate import MsgTemplate
from .BaseTopic import BaseTopic

LOG = log.get_logger()


class DiscoveryTopic(BaseTopic):
    """MQTT interface to the Discovery Topic

    This is an abstract class that provides support for the Discovery topic.
    """
    def __init__(self, mqtt, device, **kwargs):
        """Discovery Topic Constructor

        Args:
          device (device):  The Insteon object to link to.
          mqtt (mqtt.Mqtt):  The MQTT main interface.
        """
        super().__init__(mqtt, device, **kwargs)

        # This is a list of all of the discovery entries published by this
        # device
        self.entries = []

    #-----------------------------------------------------------------------
    def load_discovery_data(self, config, qos=None):
        """Load values from a configuration data object.

        Args:
          config (dict):  The mqtt section of the config dict.
          qos (int):  The default quality of service level to use.
        """
        # First check to see that discovery_topic_base is set in config
        discovery_topic_base = config.get('discovery_topic_base', None)
        if discovery_topic_base is None:
            LOG.debug("Discovery disabled, discovery_topic_base not defined.")

        # Get the device specific discovery class
        disc_class = self.device.config_extra.get('discovery_class',
                                                  self.class_name)
        class_config = config.get(disc_class, None)
        if class_config is None:
            LOG.error("%s - Unable to find discovery class %s",
                      self.device.label, disc_class)
            return

        # Loop all of the discovery entities and append them to self.topics
        entities = class_config.get('discovery_entities', None)
        if entities is None or not isinstance(entities, list):
            LOG.error("%s - No discovery_entities defined, or not a list %s",
                      self.device.label, entities)
            return
        for entity in entities:
            component = entity.get('component', None)
            if component is None:
                LOG.error("%s - No component specified in discovery entity %s",
                          self.device.label, entity)
                continue

            payload = entity.get('config', None)
            if payload is None:
                LOG.error("%s - No config specified in discovery entity %s",
                          self.device.label, entity)
                continue

            # Allowing topic to be settable in yaml, but I don't think users
            # should worry about this, there is no utility in changing it
            unique_id = self._get_unique_id(payload)
            default_topic = "%s/%s/%s/%s/config" % (discovery_topic_base,
                                                    component,
                                                    self.device.addr.hex,
                                                    unique_id)
            topic = entity.get('topic', default_topic)
            self.entries.append(MsgTemplate(topic=topic, payload=payload,
                                            qos=qos, retain=False))

    #-----------------------------------------------------------------------
    def discovery_template_data(self, **kwargs):
        """Create the Jinja templating data variables for on/off messages.

        kwargs are empty.  Only here for conformity with base class.

        Returns:
          dict:  Returns a dict with the variables available for templating.
                 including:
                 name = device name in lower case
                 address = hexadecimal address of device as a string
                 name_user_case = device name in the case entered by the user
                 engine = device engine version (i1, i2, i2cs)
                 model = device model string
                 firmware = device firmware version
                 modem_addr = hexadecimal address of modem as a string
                 device_info_template = a template defined in config.yaml
                 <<topics>> = topic keys as defined in the config.yaml file
                      are available as variables
        """
        # Set up the variables that can be used in the templates.
        data = self.base_template_data(**kwargs)

        # Insert Topics from topic classes
        data.update(self.topics)

        data['name_user_case'] = self.device.addr.hex
        if self.device.name_user_case:
            data['name_user_case'] = self.device.name_user_case

        engine_map = {0: 'i1', 1: 'i2', 2: 'i2cs'}
        data['engine'] = engine_map.get(self.device.db.engine, 'Unknown')
        data['model'] = self.device.db.desc
        data['firmware'] = self.device.db.firmware
        data['modem_addr'] = self.device.modem.addr.hex

        # Finally, render the device_info_template
        device_info_template = jinja2.Template(self.mqtt.device_info_template)
        try:
            data['device_info_template'] = device_info_template.render(data)
        except jinja2.exceptions.UndefinedError as exc:
            LOG.error("Error rendering device_info_template: %s", exc)
            LOG.error("Template was: \n%s",
                      self.mqtt.device_info_template.strip())
            LOG.error("Data passed was: %s", data)

        return data

    #-----------------------------------------------------------------------
    def publish_discovery(self, device, **kwargs):
        """Device on/off callback.

        This is triggered via ...

        Args:
          device (device):   The Insteon device that changed.
          kwargs (dict): The arguments to pass to discovery_template_data
        """
        LOG.info("MQTT received discovery %s on: %s", device.label, kwargs)

        data = self.discovery_template_data(**kwargs)

        for entry in self.entries:
            entry.publish(self.mqtt, data, retain=False)

    #-----------------------------------------------------------------------
    def _get_unique_id(self, config):
        """Extracts the unique id from the rendered payload.

        This renders the discovery payload, the decodes the json payload
        back into a dict and extracts the unique_id.  This may seem a little
        circuitous, but any solution requires rendering of the config and
        json parsing if we want to know the unique_id.

        Args:
          config (dict):  The mqtt section of the config dict.

        Returns:
          unique_id (str) or None if there was an error.
        """
        config_template = jinja2.Template(config)
        data = self.discovery_template_data()
        ret = None
        # First render template
        try:
            config_rendered = config_template.render(data)
        except jinja2.exceptions.UndefinedError as exc:
            LOG.error("Error rendering config template: %s", exc)
            LOG.error("Template was: \n%s",
                      config.strip())
            LOG.error("Data passed was: %s", data)
        else:
            # Second, parse rendered result as json
            # config_str = config_rendered.decode('utf-8')
            try:
                config_json = json.loads(config_rendered)
            except json.JSONDecodeError as exc:
                LOG.error("Error parsing config as json: %s", exc)
                LOG.error("Config output was: \n%s",
                          config_rendered.strip())
            else:
                # Third check for existence of unique_id or uniq_id
                ret = config_json.get('unique_id',
                                      config_json.get('uniq_id', None))
                if ret is None:
                    LOG.error("Unique_id was not specified in config: %s",
                              config_rendered)
        return ret

    #-----------------------------------------------------------------------
