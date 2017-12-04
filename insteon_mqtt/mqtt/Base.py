#===========================================================================
#
# MQTT Base device
#
#===========================================================================
import json
import jinja2
from .. import log
from . import util

LOG = log.get_logger()


class Base:
    """TODO: doc
    """
    def __init__(self, mqtt, device):
        """TODO: doc
        """
        self.mqtt = mqtt
        self.device = device

    #-----------------------------------------------------------------------
    def load_topic_template(self, name, value):
        """TODO: doc
        """
        if not value:
            return

        value = util.clean_topic(value)

        dev = self.device
        data = {
            "address" : dev.addr.hex,
            "name" : dev.name if dev.name else dev.addr.hex,
            }

        # Save the raw topic template string for error messages.
        value_key = name + "_str"
        setattr(self, value_key, value)

        # Create the template object and render the topic string.
        try:
            templ = jinja2.Template(value)
            setattr(self, name, templ.render(data))
        except:
            LOG.exception("Error rendering topic template '%s'", name)

    #-----------------------------------------------------------------------
    def load_payload_template(self, name, value):
        """TODO: doc
        """
        if not value:
            return

        # Save the raw value for future errors.
        value_key = name + "_str"
        setattr(self, value_key, value)

        # Create the Jinja template.
        try:
            templ = jinja2.Template(value)
            setattr(self, name, templ)
        except:
            LOG.exception("Error creating payload template '%s'", name)

    #-----------------------------------------------------------------------
    def render(self, template_name, data):
        """TODO: doc
        """
        templ = getattr(self, template_name)
        try:
            return templ.render(data)
        except:
            LOG.exception("MQTT failed to render template %s: %s with '%s'",
                          template_name, getattr(self, template_name + "_str"),
                          data)
            return None

    #-----------------------------------------------------------------------
    def input_to_json(self, payload, template_name):
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
        value = self.render(template_name, data)

        LOG.debug("Input template %s render: '%s'", template_name, value)
        if not value:
            return

        try:
            return json.loads(value)
        except:
            LOG.exception("Invalid JSON message result for %s: %s" %
                          (template_name, value))
            return None

    #-----------------------------------------------------------------------
