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
from . import log
from .Address import Address

LOG = log.get_logger()

class Scenes:
    """Scenes Config File Class

    This class creates an object that holds and manages the scenes file
    definitions.
    """
    def __init__(self, modem, path):
        self.modem = modem
        self.path = path
        self.data = []
        self.entries = []
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
        # Create basic entry for this scene
        new_entry = SceneEntry.from_link_entry(self, dev_addr, entry)
        new_controller = new_entry.controllers[0]
        new_responder = new_entry.responders[0]

        # Loop existing Scenes
        found_controller = None
        for scene in self.entries:
            found_controller = scene.find_controller(new_controller)
            found_responder = scene.find_responder(new_responder)
            if found_controller is not None:
                if found_responder is not None:
                    # 1 Update responder if necessary
                    if new_responder.data_1 is not None:
                        found_responder.data_1 = new_responder.data_1
                    if new_responder.data_2 is not None:
                        found_responder.data_2 = new_responder.data_2
                    if new_responder.data_3 is not None:
                        found_responder.data_3 = new_responder.data_3
                else:
                    if len(scene.controllers) > 1:
                        # 2 Split controller from this scene and make new scene
                        # First delete controller record in orig scene
                        scene.del_controller(found_controller)
                        # Take Scene Name if this is Modem
                        if (found_controller.device is not None and
                                found_controller.device == self.modem and
                                scene.name is not None):
                            new_entry.name = scene.name
                            scene.name = None
                        # Second merge in responders from old into new one
                        for old_responder in scene.responders:
                            new_entry.append_responder(old_responder)
                        # Third append new record to end
                        self.append_scene(new_entry)
                    else:
                        # 3 Append only new responder
                        scene.append_responder(new_responder)
                        # See if we can compress with another scene now
                        self._merge_by_responders(scene)
                break  # Found controller entry, end looping scenes
        if not found_controller:
            # 4 No matching scene_entry, append a new one
            self.append_scene(new_entry)

    #-----------------------------------------------------------------------
    def _merge_by_responders(self, test_scene):
        """Test if Passed Scene has the same responders as any other scene, if
        it does, merge with that scene

        Args:
          scene  (SceneEntry): The Passed Scene

        """
        for scene in self.entries:
            if test_scene == scene:
                # Can't merge with ourselves
                continue
            if len(test_scene.responders) == len(scene.responders):
                if Counter(test_scene.responders) == Counter(scene.responders):
                    for new_controller in test_scene.controllers:
                        scene.append_controller(new_controller)
                    if test_scene.name is not None:
                        scene.name = test_scene.name
                    self.del_scene(test_scene)
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

            if self.data is None:
                self.data = []

            self._init_scene_entries()

            # First fix any Modem Controllers that lack a proper group
            self._assign_modem_group()

            # Parse yaml, add groups to modem, and push definitions to devices
            self.populate_scenes()

    #-----------------------------------------------------------------------
    def _init_scene_entries(self):
        """Creates the initial Scene Entries
        """
        self.entries = []
        for scene in self.data:
            self.entries.append(SceneEntry(self, scene))

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
        if orgCount != 0 and diffCount / orgCount <= 0.05:
            os.remove(backup)
            backup = ''

    #-----------------------------------------------------------------------
    def populate_scenes(self):
        """Push the Config Scenes to the Device Config Databases

        Empty the config databases on each device. Then populate the config
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

        # Push Scenes to Devices and DeviceEntrys
        for scene in self.entries:
            # Generate Controller Entries
            for controller in scene.controllers:
                for responder in scene.responders:
                    if controller.device is not None:
                        controller.device.db_config.add_from_config(responder,
                                                                    controller)

            # Generate Responder Entries
            for responder in scene.responders:
                for controller in scene.controllers:
                    if responder.device is not None:
                        responder.device.db_config.add_from_config(controller,
                                                                   responder)

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
        updated = False
        for scene in self.entries:
            for controller in scene.controllers:
                if (controller.device is not None
                        and controller.device.type() == "Modem"
                        and controller.group <= 0x01):
                    updated = True

                    # Get and set the next available group id
                    controller.group = self.modem.db.next_group()

        # All done save the config file if necessary
        if updated:
            self.save()

    #-----------------------------------------------------------------------
    def update_scene(self, scene):
        """Writes Changes in a SceneEntry to the SceneManager

        A scene may not be present in the SceneManager, this occurs when a
        new template scene is made from a link database entry.  In such cases
        ignore the update request.

        Changes will only be saved to disk on a call to self.save()

        Args:
          scene:    (SceneEntry) The scene
        """
        if scene.index is not None and self.data[scene.index] != scene.data:
            self.data[scene.index] = scene.data

    #-----------------------------------------------------------------------
    def append_scene(self, scene):
        """Adds a new SceneEntry to the SceneManager

        Changes will only be saved to disk on a call to self.save()

        Args:
          scene:    (SceneEntry) The scene
        """
        self.entries.append(scene)
        self.data.append(scene.data)

    def del_scene(self, scene):
        """Deletes a SceneEntry from the SceneManager

        Changes will only be saved to disk on a call to self.save()

        Args:
          scene:    (SceneEntry) The scene to be deleted
        """
        if scene.index is not None:
            del self.entries[scene.index]
            del self.data[scene.index]

#===========================================================================


class SceneEntry:
    """Scene Entry Class

    Parses each Scene Entry into a unified and manageable object.
    """

    #-----------------------------------------------------------------------
    def __init__(self, scene_manager, scene):
        """Initializes Scene Entry

        Args:
          scene_manager: (Scenes) The scene manager object
          scene:    (dict): The data read from the config file.
        """
        self.scene_manager = scene_manager
        self._name = None
        self._controllers = []
        self._responders = []
        self._data = scene
        if 'name' in scene:
            self._name = scene['name']
        if 'controllers' in scene:
            for controller in scene['controllers']:
                controller = SceneDevice(self, controller, is_controller=True)
                self._controllers.append(controller)
                controller.make_pretty()
        if 'responders' in scene:
            for responder in scene['responders']:
                responder = SceneDevice(self, responder)
                self._responders.append(responder)
                responder.make_pretty()

    #-----------------------------------------------------------------------
    @staticmethod
    def from_link_entry(scene_manager, dev_addr, entry):
        """Generate a Scene Entry from a Device Link Entry

        Generates what a completely new SceneEntry would look like from a
        DB Entry.  Because a DB Entry is only half of a link pair, there is
        some information we will be lacking when we generate this scene.

        Args:
          dev_addr   (Address): Address of device entry is on.
          entry      (DeviceEntry/ModemEntry): Entry.

        Returns:
          (SceneEntry)
        """
        scene = {"controllers": [], "responders": []}
        dev_addr = str(dev_addr)
        entry_addr = str(entry.addr)

        if entry.is_controller:
            scene['controllers'].append({dev_addr: {'group': entry.group,
                                                    'data_1': entry.data[0],
                                                    'data_2': entry.data[1],
                                                    'data_3': entry.data[2]}})
            scene['responders'].append(entry_addr)
        else:
            scene['responders'].append({dev_addr: {'data_1': entry.data[0],
                                                   'data_2': entry.data[1],
                                                   'data_3': entry.data[2]}})
            if entry.group > 0x01:
                scene['controllers'].append({entry_addr: entry.group})
            else:
                scene['controllers'].append(entry_addr)
        return SceneEntry(scene_manager, scene)

    #-----------------------------------------------------------------------
    @property
    def index(self):
        """Returns the index of the scene on the scene_manager
        """
        index = None
        for scene_i in range(len(self.scene_manager.entries)):
            if self.scene_manager.entries[scene_i] == self:
                index = scene_i
                break
        return index

    #-----------------------------------------------------------------------
    @property
    def name(self):
        """Returns the scene name if there is one
        """
        return self._name

    #-----------------------------------------------------------------------
    @name.setter
    def name(self, name):
        """Sets the name value

        Args:
          name:    The name string
        """
        if name != self._name:
            self._name = name
            if self._name is not None:
                self._data['name'] = self._name
            else:
                del self._data['name']
            self.scene_manager.update_scene(self)

    #-----------------------------------------------------------------------
    @property
    def data(self):
        """Returns the raw data for the scene entry
        """
        return self._data

    #-----------------------------------------------------------------------
    @property
    def controllers(self):
        """Returns the controller list
        """
        return self._controllers

    #-----------------------------------------------------------------------
    @property
    def responders(self):
        """Returns the responder list
        """
        return self._responders

    #-----------------------------------------------------------------------
    def append_controller(self, controller):
        """Appends a Controller to the SceneEntry

        Args:
          controller:    (SceneDevice) The controller
        """
        self._controllers.append(controller)
        self._data['controllers'].append(controller.data)

    #-----------------------------------------------------------------------
    def append_responder(self, responder):
        """Appends a responder to the SceneEntry

        Args:
          responder:    (SceneDevice) The responder
        """
        self._responders.append(responder)
        self._data['responders'].append(responder.data)

    #-----------------------------------------------------------------------
    def find_controller(self, controller):
        """Finds a Controller to the SceneEntry

        Args:
          controller:    (SceneDevice) The controller
        Returns:
          The controller
        """
        ret = None
        for my_controller in self.controllers:
            if controller.addr == my_controller.addr:
                # Ensure that group matches for controllers
                if my_controller.group == 0x00:
                    my_controller.group = 0x01
                if controller.group == 0x00:
                    controller.group = 0x01
                if my_controller.group == controller.group:
                    ret = my_controller
        return ret

    #-----------------------------------------------------------------------
    def find_responder(self, responder):
        """Appends a Responder to the SceneEntry

        Args:
          responder:    (SceneDevice) The responder
        Returns:
          The responder
        """
        ret = None
        for my_responder in self.responders:
            if responder.addr == my_responder.addr:
                ret = my_responder
        return ret

    #-----------------------------------------------------------------------
    def del_controller(self, controller):
        """Deletes a Controller in the SceneEntry

        Args:
          controller:    (SceneDevice) The controller
        """
        if controller.index is not None:
            del self._controllers[controller.index]
            del self._data['controllers'][controller.index]
            self.scene_manager.update_scene(self)

    #-----------------------------------------------------------------------
    def update_device(self, device):
        """Writes Chagnes in a SceneDevice to the SceneEntry

        Args:
          device:    (SceneDevice) The device
          data: The raw data that replaces the device entry
        """
        update = False
        if device.index is None:
            LOG.exception("Device %s %s not defined in scene ", device.addr,
                          device.label)
        else:
            if device.is_controller:
                if self._data['controllers'][device.index] != device.data:
                    self._data['controllers'][device.index] = device.data
                    update = True
            else:
                if self._data['responders'][device.index] != device.data:
                    self._data['responders'][device.index] = device.data
                    update = True
            # Push the changes to the scene_manager data
            if update:
                self.scene_manager.update_scene(self)

#===========================================================================


class SceneDevice:
    """A Device Definition Contained in a SceneEntry

    Parses all details about a device definition, into a managable object.
    For devices that are known we can determine a lot of information
    """

    def __init__(self, scene, data, is_controller=False):
        """Initializes Object

        Args:
          TODO
        """
        self.scene = scene
        self.is_controller = is_controller
        self._modem = self.scene.scene_manager.modem
        self._data = data

        self.device = None
        self._addr = None

        # Start with the default assumption that only a device is specified
        # with no other details
        self._group = 0x01
        self._label = data
        # TODO we need some default values for these
        self._data_list = [None, None, None]
        if isinstance(data, dict):
            # The key is the device string
            self._label = next(iter(data))
            if isinstance(data[self._label], int):
                # The value is the group
                self._group = data[self._label]
            else:
                # This is a dict try and extract values
                if 'group' in data[self._label]:
                    self._group = data[self._label]['group']
                if 'data_1' in data[self._label]:
                    self._data_list[0] = data[self._label]['data_1']
                if 'data_2' in data[self._label]:
                    self._data_list[1] = data[self._label]['data_2']
                if 'data_3' in data[self._label]:
                    self._data_list[2] = data[self._label]['data_3']

    def make_pretty(self):
        """Converts the Label from Address to a Name if one can be found
        """
        # Try and find this device
        self.device = self._modem.find(self._label)
        if self.device is not None:
            self._addr = self.device.addr
            self.label = self.device.name
        else:
            # This will break if a name is used that doesn't exist
            self._addr = Address(self._label)
        self.fix_modem()

    def fix_modem(self):
        """Cleans up modem devices

        They do not need data values, as these are irrelevant
        """
        if self.device == self._modem and self.style == 0:
            # Modem Data values are irrelevant and we ignore them
            self._data_list = [None, None, None]
            if 'data_1' in self._data[self._label]:
                del self._data[self._label]['data_1']
            if 'data_2' in self._data[self._label]:
                del self._data[self._label]['data_2']
            if 'data_3' in self._data[self._label]:
                del self._data[self._label]['data_3']
            if self._group > 0x01:
                self._data[self._label] = self._group
            else:
                self._data = self._label
            self.scene.update_device(self)

    @property
    def style(self):
        # Try to match the style used by the config file
        # Style=0:
        #   {device: {'group': group}}
        # Style=1:
        #   {device:group}
        # Style=2:
        #   str(device)
        style = 2
        if isinstance(self._data, dict):
            if isinstance(self._data[self._label], int):
                # The value is the group
                style = 1
            else:
                # This is a dict try and extract values
                style = 0
        return style

    #-----------------------------------------------------------------------
    @property
    def index(self):
        """Returns the index of the device in the scene
        """
        index = None
        if self.is_controller:
            for dev_i in range(len(self.scene.controllers)):
                if self.scene.controllers[dev_i] == self:
                    index = dev_i
                    break
        else:
            for dev_i in range(len(self.scene.responders)):
                if self.scene.responders[dev_i] == self:
                    index = dev_i
                    break
        return index

    #-----------------------------------------------------------------------
    @property
    def data(self):
        """Returns the raw data suitable for Ruamel for the SceneDevice
        """
        return self._data

    #-----------------------------------------------------------------------
    @property
    def addr(self):
        """Returns the addr value
        """
        return self._addr

    #-----------------------------------------------------------------------
    @property
    def group(self):
        """Returns the group value
        """
        return self._group

    #-----------------------------------------------------------------------
    @group.setter
    def group(self, value):
        """Sets the group value

        Args:
          value:    (int)The group value
        """
        if value != self._group:
            self._group = value
            if self.style == 0:
                self._data[self._label]['group'] = self._group
            elif self.style == 1:
                self._data[self._label] = self._group
            elif self.style == 2:
                self._data = {self._label: self._group}
            self.scene.update_device(self)

    #-----------------------------------------------------------------------
    @property
    def label(self):
        """Returns the label value
        """
        return self._label

    #-----------------------------------------------------------------------
    @label.setter
    def label(self, value):
        """Sets the label value

        Args:
          value:    (int)The label value
        """
        if value != self._label:
            if self.style <= 1:
                self._data[value] = self._data[self._label]
                del self._data[self._label]
            elif self.style == 2:
                self._data = value
            self._label = value
            self.scene.update_device(self)

    @property
    #-----------------------------------------------------------------------
    def raw_data_list(self):
        """Returns the Data1-3 values as a list
        """
        # TODO this is a bad way to solve this.
        data_1 = self._data_list[0] if self._data_list[0] is not None else 0
        data_2 = self._data_list[1] if self._data_list[1] is not None else 0
        data_3 = self._data_list[2] if self._data_list[2] is not None else 0
        return [data_1, data_2, data_3]

    @raw_data_list.setter
    #-----------------------------------------------------------------------
    def raw_data_list(self, data_list):
        """Sets the raw data1-3 values via a list
        """
        if len(data_list) == 3:
            self.data_1 = data_list[0]
            self.data_2 = data_list[1]
            self.data_3 = data_list[2]

    @property
    #-----------------------------------------------------------------------
    def data_1(self):
        """Returns the Data1 raw values
        """
        return self._data_list[0]

    @data_1.setter
    #-----------------------------------------------------------------------
    def data_1(self, value):
        """Sets the raw data1 value
        """
        self.write_data(0, value)

    @property
    #-----------------------------------------------------------------------
    def data_2(self):
        """Returns the Data1 raw values
        """
        return self._data_list[1]

    @data_2.setter
    #-----------------------------------------------------------------------
    def data_2(self, value):
        """Sets the raw data2 value
        """
        self.write_data(1, value)

    @property
    #-----------------------------------------------------------------------
    def data_3(self):
        """Returns the Data3 raw values
        """
        return self._data_list[2]

    @data_3.setter
    #-----------------------------------------------------------------------
    def data_3(self, value):
        """Sets the raw data3 value
        """
        self.write_data(2, value)

    #-----------------------------------------------------------------------
    def write_data(self, position, value):
        """Sets the raw data1 value
        """
        names = ['data_1', 'data_2', 'data_3']
        name = names[position]
        # Ignore Writes to Modem Data Values, they are never used
        if self.device == self._modem:
            return
        # TODO probably insert the concept of default values in here
        if value != self._data_list[position]:
            self._data_list[position] = value
            if self.style == 0:
                self._data[self._label][name] = value
            elif self.style == 1:
                self._data[self._label] = {'group': self._group,
                                           name: value}
            elif self.style == 2:
                self._data = {self._label: {'group': self._group,
                                            name: value}}
            self.scene.update_device(self)
