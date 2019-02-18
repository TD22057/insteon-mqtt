#===========================================================================
#
# MQTT topic and payload template
#
#===========================================================================
import json
import jinja2
from .. import log

LOG = log.get_logger()


class MsgTemplate:
    """MQTT message template helper.

    This class stores a topic and payload jinja2 template for use in
    formatting and parsing MQTT messages.
    """

    @staticmethod
    def clean_topic(topic):
        """Clean up input topics

        This removes any trailing '/' characters and strips whitespace
        from the ends.

        Arg:
          topic (str):  The input topic.

        Returns:
          str: Returns the cleaned topic.
        """
        topic = topic.strip()
        if topic.endswith("/"):
            return topic[:-1].strip()

        return topic.strip()

    #-----------------------------------------------------------------------
    def __init__(self, topic, payload, qos=0, retain=None):
        """Constructor

        Args:
          topic (str):  The topic template to use.
          payload (str):  The payload template to use.
          qos (int):  Quality of service to use when publishing.
          retain (bool):  None to use the MQTT class retain flag.  Otherwise
                 the retain flag to use.
        """
        self.qos = qos
        self.retain = retain

        # Keep the original string around for better log and error messages.
        self.topic_str = topic
        self.topic = None if topic is None else jinja2.Template(topic)

        self.payload_str = payload
        self.payload = None if payload is None else jinja2.Template(payload)

    #-----------------------------------------------------------------------
    def load_config(self, config, topic, payload, qos=None):
        """Load templates from a configuration file.

        If the topic or payload doesn't exist in the config, the value from
        the constructor is used.

        Args:
          config (dict):  The configuration dictionary to load from.
          topic (str):  The name of the topic field in the config dict.
                This may None to make a null-op template.
          payload (str):  The name of the payload field in the config dict.
                  This may None to make a null-op template.
          qos (int):  Quality of service to use when publishing.  If None, use
                      the constructor value.
        """
        if qos is not None:
            self.qos = qos

        template = config.get(topic, None)
        if template is not None:
            self.topic_str = template
            self.topic = jinja2.Template(template)

        template = config.get(payload, None)
        if template is not None:
            self.payload_str = template
            self.payload = jinja2.Template(template)

    #-----------------------------------------------------------------------
    def render_topic(self, data, silent=False):
        """Render the topic template.

        Args:
          data (dict):  Data dictionary with template variables to pass to the
               jinja template.
          silent (bool) True to silence error logs.

        Returns:
          str:  Returns the rendered topic.  This may be None if the
          constructor or config topic data was None.
        """
        return self._render(self.topic_str, self.topic, data, silent)

    #-----------------------------------------------------------------------
    def render_payload(self, data, silent=False):
        """Render the payload template.

        Args:
          data (dict):  Data dictionary with template variables to pass to the
               jinja template.
          silent (bool) True to silence error logs.

        Returns:
          str:  Returns the rendered payload.  This may be None if the
          constructor or config topic data was None.
        """
        return self._render(self.payload_str, self.payload, data, silent)

    #-----------------------------------------------------------------------
    def publish(self, mqtt, data, retain=None):
        """Publish a message.

        If either the topic or payload fails to render, nothing is done.

        Args:
          mqtt (Mqtt):  The MQTT client to publish to.
          data (dict):  Data dictionary with template variables to pass to the
               jinja templates.
          retain (bool):  None to use the class retain flag.  Otherwise
                 the retain flag to use.
        """
        topic = self.render_topic(data)
        payload = self.render_payload(data)
        retain = retain if retain is not None else self.retain

        if topic and payload:
            mqtt.publish(topic, payload, self.qos, retain)

    #-----------------------------------------------------------------------
    def to_json(self, payload, silent=False):
        """Convert an MQTT payload to a JSON data.

        The payload template can only have 'value' and 'json' variables.  The
        input payload is converted to json if possible and the it's passed to
        the payload template which must convert it to valid json.  That
        parsed json result is returned.

        Args:
          payload (bytes):  The input MQTT payload as bytes.
          silent (bool):  True to silence error logs.

        Returns:
          dict:  Returns the parsed JSON dictionary or None if parsing fails.
        """
        # Convert the MQTT message into a string.  This is needed for saner
        # comparisons and because JSON is UTF-8.
        payload_str = payload.decode('utf-8')

        # Create the inputs to pass to the template.
        data = {
            'value' : payload_str,
            'json' : None,
            }
        try:
            data['json'] = json.loads(payload_str)
        except:
            pass

        # Use the input to convert the payload to a JSON string.
        value = self.render_payload(data, silent)
        if not silent:
            LOG.debug("Input template render: '%s'", value)
        if value is None:
            return None

        try:
            return json.loads(value)
        except:
            LOG.exception("Invalid JSON message %s from template %s", value,
                          self.payload_str)
            return None

    #-----------------------------------------------------------------------
    def _render(self, raw, template, data, silent=False):
        """Render a template and return None if it Fails.

        Args:
          raw (str):  Raw template string - used in logging errors.
          template:  The Jinja template object to use.
          data (dict):  The data dictionary to pass to the template.
          silent (bool):  True to silence error logs.

        Returns:
          str:  Returns the rendered value or None if if fails.
        """
        if template is None:
            return None

        try:
            return template.render(data)
        except:
            if not silent:
                LOG.exception("Error rendering template '%s' with data: %s",
                              raw, data)
            return None

    #-----------------------------------------------------------------------
