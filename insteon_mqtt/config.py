#===========================================================================
#
# Configuration file utiltiies.
#
#===========================================================================

__doc__ = """Configuration file utilties
"""

#===========================================================================
import os.path
import re
import yaml
from cerberus import Validator
from cerberus.errors import BasicErrorHandler
from . import device

# Configuration file input description to class map.
devices = {
    # Key is config file input.  Value is tuple of (class, **kwargs) of the
    # class to use and any extra keyword args to pass to the constructor.
    'dimmer' : (device.Dimmer, {}),
    'battery_sensor' : (device.BatterySensor, {}),
    "ezio4o": (device.EZIO4O, {}),
    'fan_linc' : (device.FanLinc, {}),
    'hidden_door' : (device.HiddenDoor, {}),
    'io_linc' : (device.IOLinc, {}),
    'keypad_linc' : (device.KeypadLincDimmer, {}),
    'keypad_linc_sw' : (device.KeypadLinc, {}),
    'leak' : (device.Leak, {}),
    'mini_remote1' : (device.Remote, {'num_button' : 1}),
    'mini_remote4' : (device.Remote, {'num_button' : 4}),
    'mini_remote8' : (device.Remote, {'num_button' : 8}),
    'motion' : (device.Motion, {}),
    'outlet' : (device.Outlet, {}),
    'smoke_bridge' : (device.SmokeBridge, {}),
    'switch' : (device.Switch, {}),
    'thermostat' : (device.Thermostat, {}),
    }


#===========================================================================
def validate(path):
    """Validates the configuration file against the defined schema

    Args:
      path:  The file to load

    Returns:
      string: the failure message text or an empty string if no errors
    """
    error = ""

    # Check the main config file first
    document = None
    with open(path, "r") as f:
        document = yaml.load(f, Loader)
    error += validate_file(document, 'config-schema.yaml', 'configuration')

    # Check the Scenes file
    insteon = document.get('insteon', {})
    scenes_path = insteon.get('scenes', None)
    if scenes_path is not None:
        with open(scenes_path, "r") as f:
            document = yaml.load(f, Loader)
        # This is a bit hacky, we have to move the scenes contents into a
        # root key because cerberus has to have a root key
        scenes = {"scenes": document}
        error += validate_file(scenes, 'scenes-schema.yaml', 'scenes')

    return error


#===========================================================================
def validate_file(document, schema_file, name):
    """ This is used to validate a generic yaml file.

    We use it to validate both the config and scenes files.

    Returns:
      (str): An error message string, or an empty string if no errors.
    """
    basepath = os.path.dirname(__file__)
    schema = None
    schema_file_path = os.path.join(basepath, 'data', schema_file)
    with open(schema_file_path, "r") as f:
        schema = yaml.load(f, Loader=yaml.Loader)

    v = IMValidator(schema, error_handler=MetaErrorHandler(schema=schema))
    valid = v.validate(document)

    if valid:
        return ""
    else:
        return """
                 ------- Validation Error -------
An error occured while trying to validate your %s file.  Please
review the errors below and fix the error.  InsteonMQTT cannot run until this
error is fixed.

""" % (name) + parse_validation_errors(v.errors)


#===========================================================================
def parse_validation_errors(errors, indent=0):
    """ This creates a nice presentation of the error for the User

    The error list looks a lot like the yaml document.  Running it through
    yaml.dump() was ok.  However, doing it this way allows us to have
    multiline error messages with nice indentations and such.
    """
    error_msg = ""
    for key in errors.keys():
        error_msg += " " * indent + str(key) + ": \n"
        for item in errors[key]:
            if isinstance(item, dict):
                error_msg += parse_validation_errors(item, indent=indent + 2)
            else:
                item = item.replace("\n", "\n  " + " " * (indent + 2))
                error_msg += " " * (indent) + "- " + str(item) + "\n"
    return error_msg


#===========================================================================
def load(path):
    """Load the configuration file.

    Args:
      path:  The file to load

    Returns:
      dict: Returns the configuration dictionary.
    """
    with open(path, "r") as f:
        return yaml.load(f, Loader)


#===========================================================================
def apply(config, mqtt, modem):
    """Apply the configuration to the main MQTT and modem objects.

    Args:
      config:  The configuration dictionary.
      mqtt (mqtt.Mqtt):  The main MQTT handler.
      modem (Modem):  The PLM modem object.
    """
    # We must load the MQTT config first - loading the insteon config
    # triggers device creation and we need the various MQTT config's set
    # before that.
    mqtt.load_config(config['mqtt'])
    modem.load_config(config['insteon'])


#===========================================================================
def find(name):
    """Find a device class from a description.

    Valid inputs are defined in the config.devices dictionary.

    Raises:
      Exception if the input device is unknown.

    Args:
      name (str):  The device type name.

    Returns:
      Returns a tuple of the device class to use for the input and
      any extra keyword args to pass to the device class constructor.
    """
    dev = devices.get(name.lower(), None)
    if not dev:
        raise Exception("Unknown device name '%s'.  Valid names are "
                        "%s." % (name, devices.keys()))

    return dev


#===========================================================================
# YAML multi-file loading helper.  Original code is from here:
# https://davidchall.github.io/yaml-includes.html (with no license so I'm
# assuming it's in the public domain).
class Loader(yaml.Loader):
    def __init__(self, file):
        """Constructor

        Args:
          file (file):  File like object to read from.
        """
        yaml.Loader.add_constructor('!include', Loader.include)
        yaml.Loader.add_constructor('!rel_path', Loader.rel_path)

        super().__init__(file)
        self._base_dir = os.path.split(file.name)[0]

    #-----------------------------------------------------------------------
    def include(self, node):
        """!include file command.  Supports:

        foo: !include file.yaml
        foo: !include [file1.yaml, file2.yaml]

        Args:
          node:  The YAML node to load.
        """
        # input is a single file to load.
        if isinstance(node, yaml.ScalarNode):
            include_file = self.construct_scalar(node)
            return self._load_file(include_file)

        # input is a list of files to load.
        elif isinstance(node, yaml.SequenceNode):
            result = []
            for include_file in self.construct_sequence(node):
                result += self._load_file(include_file)
            return result

        else:
            msg = ("Error: unrecognized node type in !include statement: %s"
                   % str(node))
            raise yaml.constructor.ConstructorError(msg)

    #-----------------------------------------------------------------------
    def _load_file(self, filename):
        """Read the requested file.
        Args:
          filename (str):  The file name to load.
        """
        path = os.path.join(self._base_dir, filename)
        with open(path, 'r') as f:
            return yaml.load(f, Loader)

    #-----------------------------------------------------------------------
    def rel_path(self, node):
        """Handles !rel_path file command.  Supports:

        scenes: !rel_path file.yaml

        Allows the use of relative paths in the config.yaml file.  Intended
        for use with scenes.

        Args:
          node:  The YAML node to load.
        """
        # input is a single file to load.
        if isinstance(node, yaml.ScalarNode):
            filename = self.construct_scalar(node)
            return os.path.join(self._base_dir, filename)

        else:
            msg = ("Error: unrecognized node type in !rel_path statement: %s"
                   % str(node))
            raise yaml.constructor.ConstructorError(msg)


#===========================================================================
class MetaErrorHandler(BasicErrorHandler):
    """ Used for adding custom fail message for a better UX

    This is part of the Cerberus yaml validation schema.

    When a test fails, this will search the contents of each meta keyword
    in each key of the search path starting from the root.  If the meta
    value contains a key with the failed test name appended with "_error"
    that message will be used in place of the standard message.

    For example if the following regex fails it creates a custom error:
    mqtt:
      schema:
        cmd_topic:
          regex: '^[^/+][^+]*[^/+#]$'
          meta:
            regex_error: Custom regex error message

    """
    messages = BasicErrorHandler.messages
    messages[0x92] = "zero or more than one rule validate, when exactly " + \
                     "one is required"

    def __init__(self, schema=None, tree=None):
        self.schema = schema
        super().__init__(tree)

    def __iter__(self):
        """ This is not implemented here either.
        """
        raise NotImplementedError

    def _format_message(self, field, error):
        """ Hijack the _format_message of the base class to insert our own
        messages.

        """
        error_msg = self._find_meta_error(error.schema_path)
        if error_msg is not None:
            return error_msg
        else:
            return super()._format_message(field, error)

    def _find_meta_error(self, error_path):
        """ Gets the meta error message if there is one

        This function recursively parses the search path for the meta keyword
        starting at the root and working updwards, so that it always returns
        the most specific meta value that it can find.
        """
        schema_part = self.schema
        error_msg = None
        for iter in range(len(error_path)):
            error_key = error_path[iter]
            if isinstance(error_key, str):
                schema_part = schema_part.get(error_key, None)
            else:
                # This is likely an int representing the position in a list
                schema_part = schema_part[error_key]
            if isinstance(schema_part, dict):
                meta = schema_part.get('meta', None)
                if meta is not None:
                    error_msg = self._find_error(meta, error_path, iter)
            elif isinstance(schema_part, list):
                continue
            else:
                break
        return error_msg

    def _find_error(self, meta, error_path, iter):
        """ Gets the failed test error message if there is one

        This function recursively parses the search path for the failed test
        keyword starting at the base of meta and working updwards, the error
        message the deepest into the error_path is returned.
        """
        error_msg = None
        for meta_iter in range(iter + 1, len(error_path)):
            if not isinstance(meta, dict):
                break
            if error_path[meta_iter] + "_error" in meta:
                meta = meta[error_path[meta_iter] + "_error"]
            else:
                break
        if isinstance(meta, str):
            error_msg = meta
        return error_msg


#===========================================================================
class IMValidator(Validator):
    """ Adds a few check_with functions to validate specific settings
    """
    def _check_with_valid_insteon_addr(self, field, value):
        """ Tests whether value is a valid Insteon Address for Insteon MQTT

        Accepts any of the following:
          - (int) in range of 0 - 0xFFFFFF
          - (str) in any case:
            - No seperators - AABBCC
            - Space, dot or colon seperators - AA.BB.CC, AA BB CC, AA:BB:CC
        """
        valid = False
        # Try Integer First
        try:
            addr = int(value)
        except ValueError:
            pass
        else:
            if addr >= 0 and addr <= 0xFFFFFF:
                valid = True

        # See if valid string form
        if not valid:
            addr = re.search(
                r"^[A-F0-9]{2}[ \.:]?[A-F0-9]{2}[ \.:]?[A-F0-9]{2}$",
                str(value), flags=re.IGNORECASE
            )
            if addr is not None:
                valid = True

        if not valid:
            self._error(field, "Insteon Addresses can be represented as: \n"
                        "aa.bb.cc, aabbcc, or aa:bb:cc")

#===========================================================================
