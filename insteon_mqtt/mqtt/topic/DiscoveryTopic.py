#===========================================================================
#
# MQTT Discovery Topic
#
#===========================================================================
import json
import jinja2
from ... import log
from ...catalog import Category
from ..MsgTemplate import MsgTemplate
from .BaseTopic import BaseTopic

LOG = log.get_logger()


class DiscoveryTopic(BaseTopic):
    """MQTT interface to the Discovery Topic

    This is an abstract class that provides support for the Discovery topic.
    All devices that support MQTT discovery should inherit this.

    Note that a call to load_discovery_data will need to be made from the
    extended classes load_config method.  Plus any devices adding additional
    variables should extend discovery_template_data.
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

        This should be called inside the device load_config() method.  Note
        that it takes the full mqtt config, not just the device subsection.

        Args:
          config (dict):  The mqtt section of the config dict.
          qos (int):  The default quality of service level to use.
        """
        # Get the device specific discovery class
        disc_class = self.device.config_extra.get('discovery_class',
                                                  self.default_discovery_cls)
        class_config = config.get(disc_class, None)
        if class_config is None:
            LOG.error("%s - Unable to find discovery class %s",
                      self.device.label, disc_class)
            return

        # Loop all of the discovery entities and append them to
        # self.rendered_topic_map
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
            if unique_id is None:
                LOG.error("%s - Error getting unique_id, skipping entry",
                          self.device.label)
                continue
            topic_base = self.mqtt.discovery_topic_base
            default_topic = "%s/%s/%s/%s/config" % (topic_base,
                                                    component,
                                                    self.device.addr.hex,
                                                    unique_id)
            topic = entity.get('topic', default_topic)
            self.entries.append(MsgTemplate(topic=topic, payload=payload,
                                            qos=qos, retain=False))

    #-----------------------------------------------------------------------
    def discovery_template_data(self, **kwargs):
        """Create the Jinja templating data variables for discovery messages.

        This should be extended by specific devices when adding additional
        variables is needed, particularly when adding unique topics from
        the yaml file.

        kwargs are pass from the publish_discovery method and are not used
        in this class.

        This is run in load_discovery_data() to get the unique_id which is
        before the topics are created, so the topic variables cannot be used as
        part of the unique_id.  This is fine, but be prepared to gracefully
        handle the absence of topics in any extension of this method.

        Returns:
          dict:  Returns a dict with the variables available for templating.
                 including:
                 name = (str) device name in lower case
                 address = (str) hexadecimal address of device as a string
                 name_user_case = (str) device name in the case entered by
                                  the user
                 engine = (str) device engine version (e.g. i1, i2, i2cs)
                 model_number = (str) device model number (e.g. 2476D)
                 model_description = (str) description (e.g. SwitchLinc Dimmer)
                 firmware = (int) device firmware version
                 dev_cat = (int) device category
                 dev_cat_name = (str) device category name
                 sub_cat = (int) device sub-category
                 modem_addr = (str) hexadecimal address of modem as a string
                 device_info_template = (jinja template) a template defined in
                                        config.yaml
                 <<topics>> = (str) topic keys as defined in the config.yaml
                              file are available as variables
        """
        # Set up the variables that can be used in the templates.
        data = self.base_template_data(**kwargs)

        # Insert Topics from topic classes
        data.update(self.rendered_topic_map)

        data['name_user_case'] = self.device.addr.hex
        if self.device.name_user_case:
            data['name_user_case'] = self.device.name_user_case

        engine_map = {0: 'i1', 1: 'i2', 2: 'i2cs'}
        data['engine'] = 'Unknown'
        if hasattr(self.device.db, 'engine'):
            data['engine'] = engine_map.get(self.device.db.engine, 'Unknown')
        data['model_number'] = 'Unknown'
        data['model_description'] = 'Unknown'
        data['dev_cat'] = 0
        data['dev_cat_name'] = 'Unknown'
        data['sub_cat'] = 0
        if self.device.db.desc is not None:
            data['model_number'] = self.device.db.desc.model
            data['model_description'] = self.device.db.desc.description
            data['dev_cat'] = int(self.device.db.desc.dev_cat)
            if isinstance(self.device.db.desc.dev_cat, Category):
                data['dev_cat_name'] = self.device.db.desc.dev_cat.name
            data['sub_cat'] = self.device.db.desc.sub_cat
        data['firmware'] = 0
        if self.device.db.firmware is not None:
            data['firmware'] = self.device.db.firmware
        data['modem_addr'] = data['address']
        if hasattr(self.device, 'modem'):
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
    def publish_discovery(self, **kwargs):
        """Publish the Discovery Message

        This is triggered from the MQTT handler.

        No kwargs are currently sent from the MQTT handler, it is a little
        hard to imagine how any such arguments could be provided but left here
        for potential use.

        Args:
          kwargs (dict): The arguments to pass to discovery_template_data
        """
        LOG.info("MQTT received discovery %s on: %s",
                 self.device.label, kwargs)

        data = self.discovery_template_data(**kwargs)

        for entry in self.entries:
            entry.publish(self.mqtt, data, retain=False)

    #-----------------------------------------------------------------------
    def _get_unique_id(self, config):
        """Extracts the unique id from the rendered payload.

        This renders the discovery payload, then decodes the json payload
        back into a dict and extracts the unique_id.  This may seem a little
        circuitous, but any solution requires rendering of the config and
        json parsing if we want to know the unique_id without requiring the
        user to enter it twice.

        Args:
          config (dict):  A single entity from the discovery_entities key.

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
