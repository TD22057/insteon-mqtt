#===========================================================================
#
# Configuration file utiltiies.
#
#===========================================================================

__doc__ = """Configuration file utilties
"""

#===========================================================================
import os.path
from ruamel.yaml import YAML
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
    'mini_remote4' : (device.Remote, {'num_button' : 4}),
    'mini_remote8' : (device.Remote, {'num_button' : 8}),
    'motion' : (device.Motion, {}),
    'outlet' : (device.Outlet, {}),
    'smoke_bridge' : (device.SmokeBridge, {}),
    'switch' : (device.Switch, {}),
    'thermostat' : (device.Thermostat, {}),
    }

base_config_dir = "" # base directory of config files

#===========================================================================
def load(path):
    """Load the configuration file.

    Args:
      path:  The file to load

    Returns:
      dict: Returns the configuration dictionary.
    """
    global base_config_dir
    base_config_dir = os.path.dirname(os.path.abspath(path))
    with open(path, "r") as f:
        yaml=YAML()
        yaml.preserve_quotes = True
        return yaml.load(f)


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
