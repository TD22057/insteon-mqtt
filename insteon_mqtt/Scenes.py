#===========================================================================
#
# Scenes file utiltiies.
#
#===========================================================================

__doc__ = """Scenes file utilties
"""

#===========================================================================
import time
import difflib
import os
from datetime import datetime
from shutil import copy
from ruamel.yaml import YAML


class Scenes:
    """Scenes Config File Class

    This class creates an object that holds and manages the scenes file
    definitions.
    """
    def __init__(self, modem, path):
        self.modem = modem
        self.path = path
        self.data = []
        self._load()

    #-----------------------------------------------------------------------
    def _load(self):
        """Load and returns the scenes file.
        """
        if self.path is not None:
            with open(self.path, "r") as f:
                yaml = YAML()
                yaml.preserve_quotes = True
                self.data = yaml.load(f)

            # Parse yaml, add groups to modem, and push definitions to devices
            self._populate_scenes()

    #-----------------------------------------------------------------------
    def save(self):
        """Saves the scenes data to file.  Creates and keeps a backup
        file if diff produced is significant in size compared to original
        file size.  The diff process is a little intensive.  We could
        consider making this a user configurable option, but it seems prudent
        to have this given the amount of work a user may put into creating
        a scenes file.
        """
        # Create a backup file first`
        ts = time.time()
        timestamp = datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H-%M-%S')
        backup = self.path + "." + timestamp
        copy(self.path, backup)

        # Save the config file
        with open(self.path, "w") as f:
            yaml = YAML()
            yaml.preserve_quotes = True
            yaml.indent(mapping=2, sequence=4, offset=2)
            yaml.dump(self.data, f)

        # Check for diff
        orgCount = 0
        with open(backup, 'r') as old:
            for line in old:  # pylint: disable=W0612
                orgCount += 1
        with open(self.path, 'r') as new:
            with open(backup, 'r') as old:
                diff = difflib.unified_diff(
                    old.readlines(),
                    new.readlines(),
                    fromfile='old',
                    tofile='new',
                )
        # Count the number of deleted lines
        diffCount = len([l for l in diff if l.startswith('- ')])
        # Delete backup if # of lines deleted or altered from original file
        # is less than 5% of original file
        if diffCount / orgCount <= 0.05:
            os.remove(backup)
            backup = ''

    #-----------------------------------------------------------------------
    def _populate_scenes(self):
        """Load scenes from a configuration dict.

        Load scenes from the configuration file.  This includes both virtual
        modem scenes and interdevice scenes. Virtual modem scenes are defined
        in software - they are links where the modem is the controller and
        devices are the responders.  The modem can have up to 253 virtual modem
        scenes which we can trigger by software to broadcast a message to
        update all of the defined devices.
        Args:
          config (object):   Configuration object.
        """
        # First fix any Modem Controllers that lack a proper group
        self._assign_modem_group()

        for scene in self.data:
            controllers = []
            responders = []

            # Gather controllers list and convert to objects
            for item in scene['controllers']:
                controllers.append(self._parse_scene_device(item))

            # Gather responders list and convert to objects
            for item in scene['responders']:
                responders.append(self._parse_scene_device(item))

            # Generate Controller Entries
            for controller in controllers:
                # Generate Link Data Fields, See DeviceEntry for documentation
                # of purposes and values
                data = bytes([controller.get('data_1', 0x03),
                              controller.get('data_2', 0x00),
                              controller.get('data_3', controller['group'])])
                for responder in responders:
                    controller['device'].db_config.add_from_config(
                        responder['device'].addr,
                        controller['group'],
                        True,
                        data
                    )

            # Generate Responder Entries
            for responder in responders:
                # Generate Link Data Fields, See DeviceEntry for documentation
                # of purposes and values
                # data_# values override everything
                data = bytes([responder.get('data_1',
                                            responder.get('level', 0xFF)),
                              responder.get('data_2',
                                            responder.get('ramp', 0x1F)),
                              responder.get('data_3',
                                            responder.get('group', 0x00))
                              ])
                for controller in controllers:
                    responder['device'].db_config.add_from_config(
                        controller['device'].addr,
                        controller['group'],
                        False,
                        data
                    )

    #-----------------------------------------------------------------------
    def _parse_scene_device(self, data):
        """Parse a device from the scene config format

        Devices can be defined in the scene config using a number of
        different formats.  This function parses all of the formats into
        single style.

        Args:
          data:   Configuration dictionary for scenes.

        Returns:
          {
          device : (Device) the device object
          device_str : (str) the string passed in the config
          group : (int) the group number of the device
          level : (int) optionally the light level
          ramp : (int) optionally the ramp rate
          }
        """
        # Start with the default assumption that only a device is specified
        # with no other details
        ret = {'group' : 0x01, 'device_str' : data}
        if isinstance(ret['device_str'], dict):
            # The key is the device string
            ret['device_str'] = next(iter(data))
            if isinstance(data[ret['device_str']], int):
                # The value is the group
                ret['group'] = data[ret['device_str']]
            else:
                # This is a dict just update the return
                ret.update(data)
        # Try and find this device
        ret['device'] = self.modem.find(ret['device_str'])
        return ret

    #-----------------------------------------------------------------------
    def _assign_modem_group(self):
        """Assigns modem group numbers to modem controller scene definitions
        that lack them

        All modem controller instances require a modem scene which requires a
        group number. The modem groups 0x00 and 0x01 are reserved and cannot be
        used as scenes.

        If modem controller entries are found in the defined scenes that
        lack proper group numbers, this function will select the next
        available group number starting from 0x03 and counting up and assign
        it to this modem scene.  This directly modifies the config object and
        saves it to disk if changes are made.

        Args:
          config (object):   Configuration object.
        """
        config_scenes = self.data
        updated = False
        for scene_i in range(len(config_scenes)):
            for def_i in range(len(config_scenes[scene_i]['controllers'])):
                definition = config_scenes[scene_i]['controllers'][def_i]
                controller = self._parse_scene_device(definition)
                if (controller['device'].type() == "Modem"
                        and controller['group'] <= 0x01):
                    updated = True

                    # Get next available group id
                    group = self.modem.db.next_group()

                    # Put group id into definitions, matching user format
                    if isinstance(definition, dict):
                        device_str = next(iter(definition))
                        if isinstance(definition[device_str], int):
                            # Format 1 = modem: group
                            config_scenes[scene_i]['controllers'][def_i][device_str] = group
                        else:
                            # Format 2 = modem: {'group': group}
                            config_scenes[scene_i]['controllers'][def_i][device_str]['group'] = group
                    else:
                        # Format 3 = modem
                        config_scenes[scene_i]['controllers'][def_i] = {'modem': group}
        # All done save the config file if necessary
        if updated:
            self.data = config_scenes
            self.save()
#===========================================================================
