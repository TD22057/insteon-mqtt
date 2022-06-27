#===========================================================================
#
# MQTT Discovery Topic
#
#===========================================================================
import copy
import json
import re
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
        self.disc_templates = []

        # get a copy of the global device_info_template, so that it can
        # be overriden later if needed
        self.device_info_template = copy.deepcopy(mqtt.device_info_template)

    #-----------------------------------------------------------------------
    def load_discovery_data(self, config, qos=None):
        """Load values from a configuration data object.

        This should be called inside the device load_config() method.  Note
        that it takes the full mqtt config, not just the device subsection.

        Args:
          config (dict):  The mqtt section of the config dict.
          qos (int):  The default quality of service level to use.
        """
        # Skip if discovery not enabled
        if not self.mqtt.discovery_enabled:
            return

        # Skip if device should not be discovered
        if not self.device.config_extra.get('discoverable', True):
            return

        # Get the device specific discovery class(es)
        disc_class = self.device.config_extra.get('discovery_class',
                                                  self.default_discovery_cls)
        if isinstance(disc_class, list):
            base_class = disc_class[0]
            override_classes = disc_class[1:]
        else:
            base_class = disc_class
            override_classes = []

        dev_over_classes = self.device.config_extra.get(
            'discovery_override_class',
            None)
        if dev_over_classes:
            if isinstance(dev_over_classes, list):
                override_classes.extend(dev_over_classes)
            else:
                override_classes.append(dev_over_classes)

        # handle base_class first, which must provide entities
        class_config = config.get(base_class, None)
        if class_config is None:
            LOG.error("%s - Unable to find discovery class %s",
                      self.device.label, base_class)
            return
        entities = class_config.get('discovery_entities', None)
        if entities is None:
            LOG.error("%s - No discovery_entities defined",
                      self.device.label)
            return
        if isinstance(entities, list):
            # convert old-style (unnamed) entity list to new-style (named)
            # names are 'entity' plus the 0-based index in the list
            entities = {'entity' + str(i): e for i, e in enumerate(entities)}
        elif not isinstance(entities, dict):
            LOG.error("%s - discovery_entities must be a mapping - %s",
                      self.device.label, entities)
            return
        else:
            # a copy of the entities dictionary is needed, so that overrides
            # applied later do not modify the original in the base class
            entities = copy.deepcopy(entities)

        # handle override classes
        for override_class in override_classes:
            class_config = config.get(override_class, None)
            if class_config is None:
                LOG.error("%s - Unable to find discovery class %s",
                          self.device.label, override_class)
                return
            disc_overrides = class_config.get('discovery_overrides', None)
            if disc_overrides:
                if not self._apply_discovery_overrides(entities,
                                                       disc_overrides):
                    return

        # handle overrides from device
        disc_overrides = self.device.config_extra.get('discovery_overrides',
                                                      None)
        if disc_overrides:
            if not self._apply_discovery_overrides(entities, disc_overrides):
                return

        # Loop all of the discovery entities and append them to
        # self.rendered_topic_map
        for entity in entities.values():
            if not entity.get('discoverable', True):
                continue

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

            # handle dict-style configuration
            if isinstance(payload, dict):
                payload = json.dumps(payload, indent=2)
                # replace reference to device_info as string
                # with reference as object (remove quotes)
                payload = re.sub(r'"{{\s*device_info\s*}}"', '{{device_info}}',
                                 payload)

            # Get Unique ID from payload to use in topic
            unique_id = self._get_unique_id(payload)
            if unique_id is None:
                LOG.error("%s - Error getting unique_id, skipping entry",
                          self.device.label)
                continue

            # HA's implementation of discovery only allows a very limited
            # range of characters in the node_id and object_id fields.
            # See line #30 of /homeassistant/components/mqtt/discovery.py
            # Replace any not-allowed character with underscore
            topic_base = self.mqtt.discovery_topic_base
            address_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', self.device.addr.hex)
            unique_id_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', unique_id)
            default_topic = "%s/%s/%s/%s/config" % (topic_base,
                                                    component,
                                                    address_safe,
                                                    unique_id_safe)
            self.disc_templates.append(MsgTemplate(topic=default_topic,
                                                   payload=payload,
                                                   qos=qos,
                                                   retain=False))

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
                 device_info = (str) a JSON object with info about this device,
                                     produced from its device_info_template
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

        data['availability_topic'] = self.mqtt.availability_topic

        # Finally, render the device_info_template
        try:
            device_info_template = jinja2.Template(
                json.dumps(self.device_info_template, indent=2)
            )
            data['device_info'] = device_info_template.render(data)
            # provide a 'device_info_template' alias for configurations
            # which use it
            data['device_info_template'] = data['device_info']
        except jinja2.exceptions.TemplateError as exc:
            LOG.error("Error rendering device_info_template: %s", exc)
            LOG.error("Template was: \n%s",
                      json.dumps(self.device_info_template))
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
        LOG.info("Publishing discovery for %s kwargs: %s",
                 self.device.label, kwargs)

        data = self.discovery_template_data(**kwargs)

        for entry in self.disc_templates:
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
        data = self.discovery_template_data()
        ret = None
        # First render template
        try:
            config_template = jinja2.Template(config)
            config_rendered = config_template.render(data)
        except jinja2.exceptions.TemplateError as exc:
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
    def _apply_discovery_overrides(self, entities, disc_overrides):
        for entity_key, overrides in disc_overrides.items():
            # special handling for device-level overrides
            if entity_key == 'device':
                device = self.device_info_template
                if overrides:
                    device.update(overrides)
                # delete any keys with empty string values
                keys_to_delete = []
                for key, val in device.items():
                    if val == "":
                        keys_to_delete.append(key)
                for key in keys_to_delete:
                    del device[key]
                continue

            if entity_key not in entities:
                LOG.error("%s - Entity to override was not found - %s",
                          self.device.label, entity_key)
                return False

            entity = entities[entity_key]

            if not overrides.get('discoverable', True):
                entity['discoverable'] = False
                continue

            if 'component' in overrides:
                entity['component'] = overrides['component']

            if 'config' in overrides and overrides['config']:
                config = entity['config']
                if not isinstance(config, dict):
                    LOG.error("%s - Config as string cannot be overriden - %s",
                              self.device.label, entity_key)
                    return False
                config.update(overrides['config'])
                # delete any keys with empty string values
                keys_to_delete = []
                for key, val in config.items():
                    if val == "":
                        keys_to_delete.append(key)
                for key in keys_to_delete:
                    del config[key]

        return True
