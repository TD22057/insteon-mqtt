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
    """TODO: doc
    """

    @staticmethod
    def clean_topic(topic):
        """Clean up input topics

        This removes any trailing '/' characters and strips whitespace
        from the ends.

        Arg:
          topic:  (str) The input topic.

        Returns:
         (str) Returns the cleaned topic.
        """
        topic = topic.strip()
        if topic.endswith("/"):
            return topic[:-1].strip()

        return topic.strip()

    #-----------------------------------------------------------------------
    def __init__(self, topic, payload, qos=0):
        """TODO: doc
        """
        self.qos = qos

        self.topic_str = topic
        self.topic = jinja2.Template(topic)

        self.payload_str = payload
        self.payload = jinja2.Template(payload)

    #-----------------------------------------------------------------------
    def load_config(self, config, topic, payload, qos=None):
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
    def render_topic(self, data):
        """TODO: doc
        """
        return self._render(self.topic_str, self.topic, data)

    #-----------------------------------------------------------------------
    def render_payload(self, data):
        """TODO: doc
        """
        return self._render(self.payload_str, self.payload, data)

    #-----------------------------------------------------------------------
    def publish(self, mqtt, data):
        """TODO: doc
        """
        topic = self.render_topic(data)
        payload = self.render_payload(data)
        if topic and payload:
            mqtt.publish(topic, payload, self.qos)

    #-----------------------------------------------------------------------
    def to_json(self, payload):
        """TODO: doc
        """
        # Convert the MQTT message into a string.  This is needed for
        # saner comparisons and because JSON is UTF-8.
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
        value = self.render_payload(data)
        LOG.debug("Input template render: '%s'", value)
        if value is None:
            return

        try:
            return json.loads(value)
        except:
            LOG.exception("Invalid JSON message result for %s: %s", value)
            return None

    #-----------------------------------------------------------------------
    def _render(self, raw, template, data):
        """TODO: doc
        """
        try:
            return template.render(data)
        except:
            LOG.exception("Error rendering template '%s' with data: %s",
                          raw, data)
            return None

    #-----------------------------------------------------------------------
