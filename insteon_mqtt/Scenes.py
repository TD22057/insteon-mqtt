#===========================================================================
#
# Scenes file utiltiies.
#
#===========================================================================

__doc__ = """Scenes file utilties
"""

#===========================================================================
import os
from collections import Counter
from ruamel.yaml import YAML, RoundTripRepresenter
from . import log
from .Address import Address

LOG = log.get_logger()


class SceneManager:
    """SceneManager Class

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
    def add_or_update(self, device, entry):
        """Adds a scene to the scene config, or if it is already defined
        updates that scene to match the passed entry

        This is used by the import_scenes function.  It will add a scene to
        the scene data object if the scene is not defined.  It will also
        update a scene if it is defined.

        The scene may be added/updated in the following manner
        1 Update responder if necessary
        2 Split controller from old record and make a new scene
        3 Append new responder to a scene
        4 No matching scene entry, append a new scene

        Args:
          device   (Device): The device the entry was found on.
          entry    (DeviceEntry/ModemEntry): Entry.
        """
        # Create basic entry for this scene
        new_entry = SceneEntry.from_link_entry(self, device, entry)

        # There is never more than one controller in this case
        new_controller = new_entry.controllers[0]

        # Loop existing Scenes
        found_controller = None
        for scene in self.entries:
            found_controller = scene.find_controller(new_controller)
            if found_controller is not None:
                for new_responder in new_entry.responders:
                    # Update the scene for each responder
                    self._update_scene(new_entry, found_controller,
                                       new_responder, scene)
                break
        if not found_controller:
            # 4 No matching scene_entry, append a new scene
            self.append_scene(new_entry)

    #-----------------------------------------------------------------------
    def _update_scene(self, new_entry, found_controller, new_responder, scene):
        """Adds or Updates a Responder Entry in a Scene

        Does one of Three Things:
          1. If the responder entry is found - updates it
          If no responder entry is found:
            2. Adds the responder entry if there is only one controller
            3. Splits the controller entry into its own new entry and adds the
                responder

        Args:
          new_entry (SceneEntry): The template scene entry
          found_controller (SceneDevice): The existing controller device in
            this scene.
          new_responder (SceneDevice): The new responder device to add or
            update in the scene.
          scene (SceneEntry): The existing scene entry to modify.
        """
        new_controller = new_entry.controllers[0]
        found_responder = scene.find_responder(new_responder)
        if found_responder is not None:
            # 1 found ctrl and resp link, so just update relevant
            # link data.
            found_responder.link_data = new_responder.link_data
            found_controller.link_data = new_controller.link_data
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

    #-----------------------------------------------------------------------
    def compress_controllers(self):
        """Compress Scenes Down into a Human Readable Form by Controllers

        Attempts to make things more readable to humans, by compressing
        scene defintions.  Any two definitions that have identical
        controllers are merged.

        This is a companion to compress_responders and compress_n_way.  These are
        seperate functions to that they can be called seperately using Stacks.

        This function only processes the scenes in a single pass.  If it runs
        multiple passes, it may further compress things.  However, this
        function is a bit time consuming, so can't keep looping through it.
        """
        i = 0
        while i < len(self.entries):
            found = False
            test_scene = self.entries[i]
            # Anything less than or equal to ourselves has already been tested
            j = i + 1
            while j < len(self.entries):
                scene = self.entries[j]
                j += 1
                # Merge controllers that have identical responders
                if Counter(test_scene.responders) == Counter(scene.responders):
                    for new_controller in test_scene.controllers:
                        scene.append_controller(new_controller)
                    if test_scene.name is not None:
                        scene.name = test_scene.name
                    self.del_scene(test_scene)
                    found = True
                    break
            if found is not True:
                # if we found something we deleted the current entry so check
                # this position again.
                i += 1

    #-----------------------------------------------------------------------
    def compress_responders(self):
        """Compress Scenes Down into a Human Readable Form by Responders

        Attempts to make things more readable to humans, by compressing
        scene defintions.  Any two definitions that have identical
        responders are merged.

        This is a companion to compress_controllers and compress_n_way.  These are
        seperate functions to that they can be called seperately using Stacks.

        This function only processes the scenes in a single pass.  If it runs
        multiple passes, it may further compress things.  However, this
        function is a bit time consuming, so can't keep looping through it.
        """
        i = 0
        while i < len(self.entries):
            found = False
            test_scene = self.entries[i]
            # Anything less than or equal to ourselves has already been tested
            j = i + 1
            while j < len(self.entries):
                scene = self.entries[j]
                j += 1
                # Merge responders that have identical controllers
                test_ctrls = test_scene.controllers
                if Counter(test_ctrls) == Counter(scene.controllers):
                    for new_responder in test_scene.responders:
                        scene.append_responder(new_responder)
                    if test_scene.name is not None:
                        scene.name = test_scene.name
                    self.del_scene(test_scene)
                    found = True
                    break
            if found is not True:
                # if we found something we deleted the current entry so check
                # this position again.
                i += 1

    #-----------------------------------------------------------------------
    def compress_n_way(self):
        """Compress Scenes Down into a Human Readable Form by Controllers

        Attempts to make things more readable to humans, by compressing
        scene defintions.  3-way or N-way links are compressed into a
        single definition..

        This is a companion to compress_responders and compress_controllers.  These
        are seperate functions to that they can be called seperately using Stacks.

        This function only processes the scenes in a single pass.  If it runs
        multiple passes, it may further compress things.  However, this
        function is a bit time consuming, so can't keep looping through it.
        """
        i = 0
        while i < len(self.entries):
            found = False
            test_scene = self.entries[i]
            # Anything less than or equal to ourselves has already been tested
            j = i + 1
            while j < len(self.entries):
                scene = self.entries[j]
                j += 1
                # Merge n-way switches
                if self._can_merge_n_way(test_scene, scene):
                    for new_controller in test_scene.controllers:
                        scene.append_controller(new_controller)
                    for new_responder in test_scene.responders:
                        scene.append_responder(new_responder)
                    if test_scene.name is not None:
                        scene.name = test_scene.name
                    self.del_scene(test_scene)
                    found = True
                    break
            if found is not True:
                # if we found something we deleted the current entry so check
                # this position again.
                i += 1

    #-----------------------------------------------------------------------
    def _can_merge_n_way(self, lhs, rhs):
        """Determines Whether two Scenes Can be Merged as N-Way Scenes

        The test is whether all of the devices (ctrl & resp) appear on both
        the left and right side

        Returns:
          True if they are N-way compatible, False otherwise
        """
        for controller in lhs.controllers:
            if (rhs.find_controller(controller) is None and
                    rhs.find_responder(controller) is None):
                return False
        for responder in lhs.responders:
            if (rhs.find_controller(responder) is None and
                    rhs.find_responder(responder) is None):
                return False
        for controller in rhs.controllers:
            if (lhs.find_controller(controller) is None and
                    lhs.find_responder(controller) is None):
                return False
        for responder in rhs.responders:
            if (lhs.find_controller(responder) is None and
                    lhs.find_responder(responder) is None):
                return False
        return True

    #-----------------------------------------------------------------------
    def _load(self):
        """Load the scenes file and push scenes to devices
        """
        if self.path is not None:
            if os.path.exists(self.path):
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
        """Saves the scenes data to file.
        """

        # This is necessary to prevent the representer from making its own
        # yaml aliases.  While aliases are helpful, the computer generated
        # ones would just confuse people.
        class Representer(RoundTripRepresenter):
            def ignore_aliases(self, data):
                return True

        if self.path is not None:
            with open(self.path, "w") as f:
                yaml = YAML()
                yaml.Representer = Representer
                yaml.preserve_quotes = True
                yaml.indent(mapping=2, sequence=4, offset=2)
                yaml.dump(self.data, f)
        else:
            LOG.error("Scenes File not Defined in Config.  Scenes not saved.")

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
        # And clear the virtual scene to group map
        self.modem.scene_map = {}

        # Then clear all devices
        for device in self.modem.devices.values():
            device.clear_db_config()

        # Push Scenes to Devices and DeviceEntrys
        for scene in self.entries:
            for controller in scene.controllers:
                if (controller.device == self.modem and 'name' and
                        scene.name is not None):
                    # Add to the virtual scene to group map
                    self.modem.scene_map[scene.name] = controller.group
                for responder in scene.responders:
                    # Generate Controller Entries
                    if (controller.device is not None and
                            controller.addr != responder.addr):
                        controller.device.db_config.add_from_config(responder,
                                                                    controller)
                    # Generate Responder Entries
                    if (responder.device is not None and
                            controller.addr != responder.addr):
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
                if (controller.device is not None and
                        controller.device.type() == "Modem" and
                        controller.group <= 0x01):
                    updated = True

                    # Get and set the next available group id
                    controller.group = self.modem.db.next_group()

        # All done save the config file if necessary
        if updated:
            self.save()

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
            del self.data[scene.index]
            del self.entries[scene.index]

#===========================================================================


class SceneEntry:
    """Scene Entry Class

    An object representation of a yaml scene.
    """

    #-----------------------------------------------------------------------
    def __init__(self, scene_manager, scene):
        """Initializes Scene Entry

        Args:
          scene_manager: (SceneManager) The scene manager object
          scene:    (dict): The parsed yaml data read from the config file.
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
                self.update_device(controller)
        if 'responders' in scene:
            for responder in scene['responders']:
                responder = SceneDevice(self, responder)
                self._responders.append(responder)
                self.update_device(responder)

    #-----------------------------------------------------------------------
    @staticmethod
    def from_link_entry(scene_manager, device, entry):
        """Generate a Scene Entry from a Device Link Entry

        Generates what a completely new SceneEntry would look like from a
        DB Entry.

        Args:
          device   (Device): The device the entry is found on.
          entry    (DeviceEntry/ModemEntry): Entry.

        Returns:
          (SceneEntry)
        """
        scene = {"controllers": [], "responders": []}
        dev_addr = str(device.addr)
        entry_addr = str(entry.addr)

        if entry.is_controller:
            # Generate the Controller section of the entry
            scene['controllers'].append(
                {dev_addr: {'group': entry.group,
                            'data_1': entry.data[0],
                            'data_2': entry.data[1],
                            'data_3': entry.data[2]}}
            )
            # Generate the Responder section
            # From a controller link, we need to find all possible responder
            # links on this device.  A multigroup device could have many.
            resp_dev = scene_manager.modem.find(entry.addr)
            found_responder = False
            if resp_dev is not None:
                for resp_entry in resp_dev.db.find_all(addr=device.addr,
                                                       group=entry.group,
                                                       is_controller=False):
                    scene['responders'].append(
                        {entry_addr: {'data_1': resp_entry.data[0],
                                      'data_2': resp_entry.data[1],
                                      'data_3': resp_entry.data[2]}}
                    )
                    found_responder = True
            if not found_responder:
                # We know nothing about the responder so set to default values
                # but this could be completely wrong.  Specifically, the group
                # could be completely wrong in which case this is entry is bad
                scene['responders'].append(entry_addr)
        else:
            # Generate the Responder section
            # Since we know the responder device already, we can just assume
            # a single responder device
            scene['responders'].append({dev_addr: {'data_1': entry.data[0],
                                                   'data_2': entry.data[1],
                                                   'data_3': entry.data[2]}})
            ctrl_dev = scene_manager.modem.find(entry.addr)
            found_ctrl = False
            if ctrl_dev is not None:
                ctrl_entry = ctrl_dev.db.find(device.addr, entry.group, True)
                if ctrl_entry is not None:
                    scene['controllers'].append(
                        {entry_addr: {'group': ctrl_entry.group,
                                      'data_1': ctrl_entry.data[0],
                                      'data_2': ctrl_entry.data[1],
                                      'data_3': ctrl_entry.data[2]}}
                    )
                    found_ctrl = True
            if not found_ctrl:
                # We know nothing about the controller so set to default values
                # the link-data may be wrong, but it doesn't seem to matter
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

    #-----------------------------------------------------------------------
    @property
    def data(self):
        """Returns the yaml data for the scene entry
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
        if controller not in self._controllers:
            self._controllers.append(controller)
            self._data['controllers'].append(controller.data)

    #-----------------------------------------------------------------------
    def append_responder(self, responder):
        """Appends a responder to the SceneEntry

        Args:
          responder:    (SceneDevice) The responder
        """
        if responder not in self._responders:
            self._responders.append(responder)
            self._data['responders'].append(responder.data)

    #-----------------------------------------------------------------------
    def find_controller(self, controller):
        """Finds a Controller to the SceneEntry

        Only matches the address and group, data1-3 do not have to match

        Args:
          controller:    (SceneDevice) The controller
        Returns:
          The controller
        """
        ret = None
        for my_controller in self.controllers:
            if (controller.addr == my_controller.addr and
                    controller.group == my_controller.group):
                ret = my_controller
        return ret

    #-----------------------------------------------------------------------
    def find_responder(self, responder):
        """Finds a Responder in the SceneEntry Using Strong Comparison

        Requires the addr and group to match, data1-3 do not have to match

        Args:
          responder:    (SceneDevice) The responder
        Returns:
          The responder
        """
        ret = None
        for my_responder in self.responders:
            if (responder.addr == my_responder.addr and
                    responder.group == my_responder.group):
                ret = my_responder
        return ret

    #-----------------------------------------------------------------------
    def del_controller(self, controller):
        """Deletes a Controller in the SceneEntry

        Args:
          controller:    (SceneDevice) The controller
        """
        if controller.index is not None:
            del self._data['controllers'][controller.index]
            del self._controllers[controller.index]

    #-----------------------------------------------------------------------
    def update_device(self, device):
        """Writes Changes in a SceneDevice to the SceneEntry

        Args:
          device:    (SceneDevice) The device
          data: The raw data that replaces the device entry
        """
        if device.is_controller:
            self._data['controllers'][device.index] = device.data
        else:
            self._data['responders'][device.index] = device.data

#===========================================================================


class SceneDevice:
    """A Device Definition Contained in a SceneEntry

    Parses all details about a device definition, into a managable object.
    """

    def __init__(self, scene, data, is_controller=False):
        """Initializes Object

        Initialization also make entries pretty, meaning it may alter the
        raw data object.  As such, it is necessary to call update_device
        after initializing a SceneDevice so that the SceneEntry raw data
        is updated.
        Args:
          scene (SceneEntry): The parent SceneEntry
          data (dict/list/str): The parsed yaml data for this device
          is_controller (Boolean): Is this device a controller?
        """
        # Default Attribute Values
        self.scene = scene
        self.is_controller = is_controller
        self.device = None
        self.addr = None
        self._modem = self.scene.scene_manager.modem
        self._yaml_data = data

        # Try and find this device and populate device attibutes
        self.device = self._modem.find(self.label)
        if self.device is not None:
            self.addr = self.device.addr
            self.label = self.device.name
            # The group for responder links on multi-group devices is stored
            # in data3.  We have to extract this early, because the group may
            # influence other settings, particularly the link_defaults
            pretty_data = self.device.link_data_to_pretty(self.is_controller,
                                                          self.link_data)
            if 'group' in pretty_data[2]:
                self.group = pretty_data[2]['group']
        else:
            # This is an device not defined in our config if it uses an
            # address string, we can work with that.
            try:
                self.addr = Address(self.label)
            except ValueError:
                msg = ("Error trying to parse the scenes file.  Found a "
                       "device that is neither defined in the config file nor "
                       "defined in the scenes file as an address: %s" %
                       self.label)
                raise Exception(msg)

        # Remove values from yaml_data if they are default values and make
        # pretty. Easiest way to do this is just to set things to themselves
        self.group = self.group
        self.link_data = self.link_data

    def __eq__(self, other):
        '''A strong comparison of devices.

        Requires address, group, and data1-3 to be the same.  Does not look
        at is_controller, but this is likely captured by data1-3 anyways. Used
        primarily by the compress_* functions
        '''
        ret = False
        self_group = self.group if self.group > 0x00 else 0x01
        other_group = other.group if other.group > 0x00 else 0x01
        if (self.addr == other.addr and self_group == other_group and
                self.link_data == other.link_data):
            ret = True
        return ret

    def __str__(self):
        self_group = self.group if self.group > 0x00 else 0x01
        subs = (self.addr, self_group, self.link_data)
        return 'Dev Addr: %s Group: %s Data1-3: %s' % subs

    def __hash__(self):
        return hash(str(self))

    @property
    def style(self):
        """Returns the Style Type of the Raw Data

        This allows us to match the user defined style.

        Style=0:
          {device: {'group': group}}
        Style=1:
          {device:group}
        Style=2:
          str(device)

        Returns:
          (int): 0-2
        """
        style = 2
        if isinstance(self._yaml_data, dict):
            # This is necessary to avoid recursion loop with self.label
            label = next(iter(self._yaml_data))
            if isinstance(self._yaml_data[label], int):
                style = 1
            elif isinstance(self._yaml_data[label], dict):
                style = 0
            elif self._yaml_data[label] is None:
                # This happens if the entry has a colon, but no dict or group
                self._yaml_data = label
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
        """Returns the parsed yaml data for the SceneDevice
        """
        return self._yaml_data

    #-----------------------------------------------------------------------
    @property
    def group(self):
        """Returns the group value
        """
        group = 0x01
        if self.style == 1:
            # The value is the group
            group = self._yaml_data[self.label]
        elif self.style == 0:
            if 'group' in self._yaml_data[self.label]:
                group = self._yaml_data[self.label]['group']
        return group

    #-----------------------------------------------------------------------
    @group.setter
    def group(self, value):
        """Sets the group value

        Args:
          value:    (int)The group value
        """
        if self.style == 0 and value > 0x01:
            if ('group' not in self._yaml_data[self.label] or
                    self._yaml_data[self.label]['group'] != value):
                self._yaml_data[self.label]['group'] = value
        if self.style == 1 and value > 0x01:
            self._yaml_data[self.label] = value
        if self.style == 2 and value > 0x01:
            self._yaml_data = {self.label: value}

        # Remove group entry in yaml_data if default value of 0x00 or 0x01
        if (self.style == 0 and 'group' in self._yaml_data[self.label] and
                value <= 0x01):
            del self._yaml_data[self.label]['group']
        elif self.style == 1 and value <= 0x01:
            self._yaml_data = self.label
        self.update_device()

    #-----------------------------------------------------------------------
    @property
    def label(self):
        """Returns the label value
        """
        if self.style < 2:
            # The key is the device string
            label = next(iter(self._yaml_data))
        else:
            label = self._yaml_data
        return label

    #-----------------------------------------------------------------------
    @label.setter
    def label(self, value):
        """Sets the label value

        Args:
          value:    (int)The label value
        """
        if self.style < 2:
            if next(iter(self._yaml_data)) != value:
                key = next(iter(self._yaml_data))
                yaml_value = self._yaml_data[key]
                del self._yaml_data[key]
                self._yaml_data[value] = yaml_value
        else:
            if self._yaml_data != value:
                self._yaml_data = value
        self.update_device()

    @property
    #-----------------------------------------------------------------------
    def link_data(self):
        """Returns the Data1-3 values as a list

        If values are not specified in yaml_data the defaults are returned.

        Values will be parsed from human readable to byte like values.
        """
        link_data = self.link_defaults
        if self.style == 0:
            if 'data_1' in self._yaml_data[self.label]:
                link_data[0] = self._yaml_data[self.label]['data_1']
            if 'data_2' in self._yaml_data[self.label]:
                link_data[1] = self._yaml_data[self.label]['data_2']
            if 'data_3' in self._yaml_data[self.label]:
                link_data[2] = self._yaml_data[self.label]['data_3']
            if self.device is not None:
                # Group is a bit special and gets added to link_data
                # a few responders (kpl) need to know group to set data_3
                link_dict = self._yaml_data[self.label].copy()
                if self.group > 0x01:
                    link_dict['group'] = self.group
                # Convert data values from human readable form
                pretty_data = self.device.link_data_from_pretty(
                    self.is_controller, link_dict
                )
                for i in range(0, 3):
                    if pretty_data[i] is not None:
                        link_data[i] = pretty_data[i]
        return link_data

    @link_data.setter
    #-----------------------------------------------------------------------
    def link_data(self, data_list):
        """Sets the raw data1-3 values via a list

        If human readable pretty names are available, will convert to those
        values on saving to yaml data

        Args:
          data_list (list[int:3]): The byte like values for data1-3
        """
        if len(data_list) != 3:
            return
        if self.device is not None:
            pretty_data = self.device.link_data_to_pretty(self.is_controller,
                                                          data_list)
        else:
            pretty_data = [{'data_1': data_list[0]},
                           {'data_2': data_list[1]},
                           {'data_3': data_list[2]}]
        orig_names = ['data_1', 'data_2', 'data_3']
        for i in range(0, 3):
            pretty_name = next(iter(pretty_data[i].keys()))
            pretty_value = pretty_data[i][pretty_name]
            # Don't delete default entries for group that is handled by group
            if (data_list[i] == self.link_defaults[i] and
                    pretty_name != 'group'):
                if self.style == 0:
                    # Default, so delete if in entry
                    if orig_names[i] in self._yaml_data[self.label]:
                        del self._yaml_data[self.label][orig_names[i]]
                    if pretty_name in self._yaml_data[self.label]:
                        del self._yaml_data[self.label][pretty_name]
            else:
                # not default, so make sure value is set
                if self.style == 0:
                    # first delete orig name
                    if orig_names[i] in self._yaml_data[self.label]:
                        del self._yaml_data[self.label][orig_names[i]]
                    self._yaml_data[self.label][pretty_name] = pretty_value
                else:
                    self._yaml_data = {self.label: {pretty_name: pretty_value}}
                    if pretty_name != 'group':
                        self._yaml_data[self.label]['group'] = self.group
        self.update_device()

    @property
    #-----------------------------------------------------------------------
    def link_defaults(self):
        """Returns the Default Data1-3 values as a list
        """
        if self.device is not None:
            ret = list(self.device.link_data(self.is_controller, self.group))
        elif self.is_controller:
            # These are the values used in base.py.  They may not be right for
            # this device, but we don't know anything else about it.
            ret = [0x03, 0x00, 0x01]
        else:
            ret = [0xff, 0x00, 0x01]
        return ret

    #-----------------------------------------------------------------------
    def update_device(self):
        """Cleans up Data and Notifies SceneEntry of Updated Data if
        SceneEntry Exists
        """
        # Remove Data dict if not necessary
        if self.style == 0 and len(self._yaml_data[self.label]) == 0:
            # There is nothing in the dict, convert to style 2
            self._yaml_data = self.label
        elif (self.style == 0 and
              'group' in self._yaml_data[self.label] and
              len(self._yaml_data[self.label]) == 1):
            # Group is the only thing in dict, convert to style 1
            self._yaml_data = {self.label: self.group}
        if self.index is not None:
            self.scene.update_device(self)
