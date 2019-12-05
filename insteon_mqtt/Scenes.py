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
from collections import Counter
from .Address import Address


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
    def add_or_update(self, dev_addr, entry):
        """Adds a scene to the scene config, or if it is already defined
        updates that scene to match the passed entry

        This is used by the import_scenes function.  It will add a scene to
        the scene data object if the scene is not defined.  It will also
        update a scene if it is defined.

        The scene may be added in the following manner
        1 Update responder if necessary
        2 Split controller from old record and make new
        3 Append only new responder
        4 No matching entry, append a new one

        Args:
          dev_addr   (Address): Address of device entry is on.
          entry      (DeviceEntry/ModemEntry): Entry.
        """
        group = entry.group
        data_1 = data_2 = data_3 = None
        # Assume controller entry
        ctrl_addr = dev_addr
        resp_addr = entry.addr
        if not entry.is_controller:
            ctrl_addr = entry.addr
            resp_addr = dev_addr
            data_1, data_2, data_3 = entry.data
        # Create basic entry for this scene
        scene_entry = self._generate_scene(ctrl_addr, resp_addr, group,
                                           data_1, data_2, data_3)
        # We loop in this odd iterator manner so that we can directly alter the
        # data
        for scene_i in range(len(self.data)):
            scene_found = self._matching_scene(scene_i, ctrl_addr, resp_addr,
                                               group, data_1, data_2, data_3,
                                               scene_entry)
            if scene_found:
                break
        # end controller loop
        if not scene_found:
            # 4 No matching scene_entry, append a new one
            self.data.append(scene_entry)
        # TODO compress scenes back down.  This process doesn't allow multi
        # controllers

    #-----------------------------------------------------------------------
    def _matching_scene(self, scene_i, ctrl_addr, resp_addr, group, data_1,
                        data_2, data_3, scene_entry):
        """Checks Whether Scene Matches Entry, Update if it Does

        This is used by the add_or_update function.

        Args:
          scene_i    (int): The iterator position of the scene to be tested
          ctrl_addr  (Address): The controller address to match
          resp_addr  (Address): The responder address to match
          group      (int): The controller group
          data_1, data_2, data_3 (int): The data for responder entries
          scene_entry: The idealized scene entry for adding or updating

        Returns:
          True if matching scene was found (scene may have been amended)
          False otherwise.
        """
        resp_found = False
        for ctrl_i in range(len(self.data[scene_i]['controllers'])):
            scene_def = self.data[scene_i]['controllers'][ctrl_i]
            if self._device_match(scene_def, ctrl_addr, group, True):
                for resp_i in range(len(self.data[scene_i]['responders'])):
                    scene_def = self.data[scene_i]['responders'][resp_i]
                    if self._device_match(scene_def, resp_addr):
                        # 1 Update responder if necessary
                        resp_found = True
                        # if we were passed D1-3 then we update them
                        if all(v is not None for v in (data_1, data_2,
                                                       data_3)):
                            self.data[scene_i]['responders'][resp_i] =\
                                scene_entry['responders'][0]
                        break  # Exit responder loop
                if not resp_found:
                    if len(self.data[scene_i]['controllers']) > 1:
                        # 2 Split controller from old and make new record
                        # First delete controller record in orig scene
                        del self.data[scene_i]['controllers'][ctrl_i]
                        # Take Scene Name if this is Modem
                        if (self.modem.find(ctrl_addr) == self.modem and
                                'name' in self.data[scene_i]):
                            scene_entry['name'] = self.data[scene_i]['name']
                            del self.data[scene_i]['names']
                        # Second merge in responders from old into new one
                        scene_entry['responders'].extend(
                            self.data[scene_i]['responders']
                        )
                        # Third append new record to end
                        self.data.append(scene_entry)
                    else:
                        # 3 Append only new responder
                        self.data[scene_i]['responders'].append(
                            scene_entry['responders'][0])
                        # See if we can compress with another scene now
                        self._compress(scene_i)
                return True  # Found controller entry
        return False  # no controller entry found

    #-----------------------------------------------------------------------
    def _device_match(self, scene_def, test_addr, group=0x01,
                      is_controller=False):
        """Tests whether the test device matches the device defined in the
        scene

        Args:
          scene_def              : The raw scene definition for this device
          test_addr     (Address): The address of the device to be checked.
          group             (int): The controlling group number
          is_controller (Boolean): Set to true if checking a controller.

        Returns:
          True if device matches, False otherwise.
        """
        ret = False
        scene_def = self._parse_scene_device(scene_def)
        if scene_def['device'] is not None:
            scene_addr = scene_def['device'].addr
        else:
            # This device is not defined in config file
            scene_addr = scene_def['device_str']
        if scene_addr == test_addr:
            if not is_controller:
                ret = True
            else:
                # Ensure that group matches for controllers
                if scene_def['group'] == 0x00:
                    scene_def['group'] = 0x01
                if group == 0x00:
                    group = 0x01
                if group == scene_def['group']:
                    ret = True
        return ret

    #-----------------------------------------------------------------------
    def _generate_scene(self, ctrl_addr, resp_addr, group, data_1=0xFF,
                        data_2=0x1F, data_3=0x00):
        """Generate a Scene Entry

        Generates what a completely new scene would look like.  This can be
        modified or amended if a partial scene is found.

        Args:
          ctrl_addr  (Address): Controller address.
          resp_addr  (Address): Responder address.
          group          (int): Controller group number.
          data_1         (int): Data 1 value
          data_2         (int): Data 2 value
          data_3         (int): Data 3 value

        Returns:
          An idealized scene entry.
        """
        ctrl_name = self._make_pretty_name(ctrl_addr)
        resp_name = self._make_pretty_name(resp_addr)
        entry = {"controllers": [], "responders": []}
        entry['controllers'].append({ctrl_name: group})
        entry['responders'].append({resp_name: {'data_1': data_1,
                                                'data_2': data_2,
                                                'data_3': data_3}})
        return entry

    #-----------------------------------------------------------------------
    def _make_pretty_name(self, addr):
        """Generate a Pretty Name For an Address

        Searches for the device by address, if found and has a pretty name
        return that.  Else return string of address.

        Args:
          addr  (Address): Address.

        Returns:
          (String): Either the pretty name of the device or the address.
        """
        name = str(addr)
        device = self.modem.find(addr)
        if device is not None:
            if device.name is not None:
                name = device.name
        return name

    #-----------------------------------------------------------------------
    def _compress(self, scene_i_test):
        """Compresses Scenes to Have the Fewest Definitions

        Args:
          scene_i_test  (int): The array position of the scene to compress

        """
        test_resp = []
        for scene_def in self.data[scene_i_test]['responders']:
            test_resp.append(self._parse_scene_device(scene_def)['device'])
        test_len = len(test_resp)
        for scene_i in range(len(self.data)):
            if scene_i == scene_i_test:
                continue
            if test_len == len(self.data[scene_i]['responders']):
                scene_resp = []
                for scene_def in self.data[scene_i]['responders']:
                    scene_resp.append(self._parse_scene_device(scene_def)['device'])
                # Tests if lists are the same
                if Counter(test_resp) == Counter(scene_resp):
                    self.data[scene_i]['controllers'].extend(
                        self.data[scene_i_test]['controllers']
                    )
                    if 'name' in self.data[scene_i_test]:
                        self.data[scene_i]['name'] = \
                            self.data[scene_i_test]['name']
                    del self.data[scene_i_test]
                    return

    #-----------------------------------------------------------------------
    def _load(self):
        """Load and returns the scenes file.
        """
        if self.path is not None:
            with open(self.path, "r") as f:
                yaml = YAML()
                yaml.preserve_quotes = True
                self.data = yaml.load(f)

            # First fix any Modem Controllers that lack a proper group
            self._assign_modem_group()

            # Parse yaml, add groups to modem, and push definitions to devices
            self.populate_scenes()

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
    def populate_scenes(self):
        """Load scenes from a configuration dict.

        Empty the config databases on each device. The populate the config
        databses from the configuration data.  This includes both virtual
        modem scenes and interdevice scenes. Virtual modem scenes are defined
        in software - they are links where the modem is the controller and
        devices are the responders.  The modem can have up to 253 virtual modem
        scenes which we can trigger by software to broadcast a message to
        update all of the defined devices.

        Args:
          config (object):   Configuration object.
        """

        # First clear modem
        self.modem.clear_db_config()

        # Then clear all devices
        for device in self.modem.devices.values():
            device.clear_db_config()

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
                    if controller['device'] is not None:
                        controller['device'].db_config.add_from_config(
                            responder['addr'],
                            controller['group'],
                            True,
                            data
                        )

            # Generate Responder Entries
            for responder in responders:
                # Generate Link Data Fields, See DeviceEntry for documentation
                # of purposes and values
                # data_# values override everything
                # TODO convert level and ramp
                data = bytes([responder.get('data_1',
                                            responder.get('level', 0xFF)),
                              responder.get('data_2',
                                            responder.get('ramp', 0x1F)),
                              responder.get('data_3',
                                            responder.get('group', 0x00))
                              ])
                for controller in controllers:
                    if responder['device'] is not None:
                        responder['device'].db_config.add_from_config(
                            controller['addr'],
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
          level : (int) optionally the light level [Not yet supported]
          ramp : (int) optionally the ramp rate [Not yet supported]
          data_1: (int) optionally the data_1 value
          data_2: (int) optionally the data_2 value
          data_3: (int) optionally the data_3 value
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
        if ret['device'] is not None:
            ret['addr'] = ret['device'].addr
        else:
            ret['addr'] = Address(ret['device_str'])
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
                if (controller['device'] is not None
                        and controller['device'].type() == "Modem"
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
