#===========================================================================
#
# Configuration file utiltiies.
#
#===========================================================================

__doc__ = """Configuration file utilties
"""

#===========================================================================
import functools
import yaml
from . import device

# Configuration file input description to class map.
devices = {
    'dimmer' : device.Dimmer,
    'motion' : device.Motion,
    'switch' : device.Switch,
    'smoke_bridge' : device.SmokeBridge,
    'mini_remote4' : functools.partial(device.Remote, num=4),
    'mini_remote8' : functools.partial(device.Remote, num=8),
    }


#===========================================================================
def load(path):
    """TODO: doc
    """
    config = yaml.load(open("config.yaml").read())
    return config


#===========================================================================
def apply(config, mqtt, modem):
    """TODO: doc
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
      name:   (str) The device type name.

    Returns:
      Returns the device class to use for the input.
    """
    name = name.lower()
    dev = devices.get(name, None)
    if not dev:
        raise Exception("Unknown device name '%s'.  Valid names are "
                        "%s." % (name, devices.keys()))

    return dev

#===========================================================================
