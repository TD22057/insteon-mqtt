#===========================================================================
#
# Configuration file utiltiies.
#
#===========================================================================

__doc__ = """Configuration file utilties
"""

#===========================================================================
import os.path
import yaml
from . import device

# Configuration file input description to class map.
devices = {
    # Key is config file input.  Value is tuple of (class, **kwargs) of the
    # class to use and any extra keyword args to pass to the constructor.
    'dimmer' : (device.Dimmer, {}),
    'battery_sensor' : (device.BatterySensor, {}),
    'fan_linc' : (device.FanLinc, {}),
    'io_linc' : (device.IOLinc, {}),
    'keypad_linc' : (device.KeypadLinc, {'dimmer' : True}),
    'keypad_linc_sw' : (device.KeypadLinc, {'dimmer' : False}),
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
