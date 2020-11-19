#===========================================================================
#
# Tests for: insteont_mqtt/Scenes.py
#
# pylint:
#===========================================================================
import pytest
import insteon_mqtt as IM
import insteon_mqtt.Scenes as Scenes
import insteon_mqtt.Address as Address
import insteon_mqtt.db.DeviceEntry as DeviceEntry
import insteon_mqtt.db.Modem as ModemDB
import insteon_mqtt.device.Base as Base
import insteon_mqtt.device.Dimmer as Dimmer
import insteon_mqtt.device.FanLinc as FanLinc
import insteon_mqtt.device.KeypadLinc as KeypadLinc
import insteon_mqtt.device.Remote as Remote


class Test_Scenes:
    def test_add_or_update(self):
        # empty
        modem = MockModem()
        scenes = Scenes.SceneManager(modem, None)

        # test updating controller entry
        scenes.data = [{'controllers': ['aa.bb.cc'],
                        'responders': ['cc.bb.aa'],
                        'name': 'test'}]
        scenes._init_scene_entries()
        entry = DeviceEntry.from_json({"data": [3, 0, 239],
                                       "mem_loc" : 8119,
                                       "group": 1,
                                       "db_flags": {"is_last_rec": False,
                                                    "in_use": False,
                                                    "is_controller": True},
                                       "addr": "cc.bb.aa"})
        device = modem.find("aa.bb.cc")
        scenes.add_or_update(device, entry)
        assert len(scenes.entries) == 1

        # test updating responder entry
        scenes.data = [{'controllers': ['cc.bb.aa'],
                        'responders': ['aa.bb.cc'],
                        'name': 'test'}]
        scenes._init_scene_entries()
        entry = DeviceEntry.from_json({"data": [3, 0, 239],
                                       "mem_loc" : 8119,
                                       "group": 1,
                                       "db_flags": {"is_last_rec": False,
                                                    "in_use": False,
                                                    "is_controller": False},
                                       "addr": "cc.bb.aa"})
        device = modem.find("aa.bb.cc")
        scenes.add_or_update(device, entry)
        assert len(scenes.entries) == 1

        # test splitting scene
        scenes.data = [{'controllers': ['ff.ff.ff', {'aa.bb.22': {'group': 22}}],
                        'responders': ['aa.bb.33'],
                        'name': 'test'}]
        scenes._init_scene_entries()
        entry = DeviceEntry.from_json({"data": [3, 0, 239],
                                       "mem_loc" : 8119,
                                       "group": 1,
                                       "db_flags": {"is_last_rec": False,
                                                    "in_use": False,
                                                    "is_controller": False},
                                       "addr": "ff.ff.ff"})
        device = modem.find("aa.bb.cc")
        scenes.add_or_update(device, entry)
        assert len(scenes.entries) == 2

        # test appending responder
        scenes.data = [{'controllers': [{'cc.bb.aa': 1}],
                        'responders': [{'aa.bb.33': {}}],
                        'name': 'test'}]
        scenes._init_scene_entries()
        entry = DeviceEntry.from_json({"data": [3, 0, 239],
                                       "mem_loc" : 8119,
                                       "group": 1,
                                       "db_flags": {"is_last_rec": False,
                                                    "in_use": False,
                                                    "is_controller": False},
                                       "addr": "cc.bb.aa"})
        device = modem.find("aa.bb.cc")
        scenes.add_or_update(device, entry)
        assert len(scenes.entries) == 1

        # test appending entire new scene
        scenes.data = [{'controllers': ['cc.bb.22'],
                        'responders': ['aa.bb.33'],
                        'name': 'test'}]
        scenes._init_scene_entries()
        entry = DeviceEntry.from_json({"data": [3, 0, 239],
                                       "mem_loc" : 8119,
                                       "group": 2,
                                       "db_flags": {"is_last_rec": False,
                                                    "in_use": False,
                                                    "is_controller": False},
                                       "addr": "cc.bb.aa"})
        device = modem.find("aa.bb.cc")
        scenes.add_or_update(device, entry)
        assert len(scenes.entries) == 2

    def test_merge_by_responders(self):
        # empty
        modem = MockModem()
        scenes = Scenes.SceneManager(modem, None)

        # test updating controller entry
        scenes.data = [{'controllers': ['aa.bb.cc'],
                        'responders': ['cc.bb.22'],
                        'name': 'test'},
                       {'controllers': ['cc.bb.11'],
                        'responders': ['cc.bb.22', 'cc.bb.aa'],
                        'name': 'test2'}]
        scenes._init_scene_entries()
        entry = DeviceEntry.from_json({"data": [3, 0, 239],
                                       "mem_loc" : 8119,
                                       "group": 1,
                                       "db_flags": {"is_last_rec": False,
                                                    "in_use": False,
                                                    "is_controller": True},
                                       "addr": "cc.bb.aa"})
        device = modem.find("aa.bb.cc")
        scenes.add_or_update(device, entry)
        scenes.compress_controllers()
        scenes.compress_responders()
        assert len(scenes.entries) == 1

    def test_populate_scenes(self):
        modem = MockModem()
        device = modem.find(Address("aa.bb.cc"))
        modem.devices[device.label] = device
        device = modem.find(Address("aa.bb.22"))
        modem.devices[device.label] = device
        scenes = Scenes.SceneManager(modem, None)
        scenes.data = [{'controllers': ['aa.bb.cc'],
                        'responders': ['aa.bb.22'],
                        'name': 'test'}]
        scenes._init_scene_entries()
        scenes.populate_scenes()

    def test_assign_modem_group(self):
        modem = MockModem()
        scenes = Scenes.SceneManager(modem, None)
        scenes.data = [{'controllers': ['ff.ff.ff'],
                        'responders': ['cc.bb.22'],
                        'name': 'test'}]
        scenes._init_scene_entries()
        scenes._assign_modem_group()
        # 20 is the current lowest allowed group number
        assert scenes.data[0]['controllers'][0]['modem'] == 20

    def test_bad_config(self):
        modem = MockModem()
        scenes = Scenes.SceneManager(modem, None)
        scenes.data = [{'controllers': [{'a1.b1.c1': None}],
                        'responders': ['cc.bb.22'],
                        'name': 'test'}]
        scenes._init_scene_entries()
        assert scenes.data[0]['controllers'][0] == 'dev - a1.b1.c1'

    def test_set_group(self):
        modem = MockModem()
        scenes = Scenes.SceneManager(modem, None)
        scenes.data = [{'controllers': [{'a1.b1.c1': {'data_1': 0}}],
                        'responders': ['cc.bb.22'],
                        'name': 'test'}]
        scenes._init_scene_entries()
        scenes.entries[0].controllers[0].group = 2
        assert scenes.data[0]['controllers'][0]['dev - a1.b1.c1']['group'] == 2

    def test_Dimmer_scenes_same_ramp_rate(self):
        modem = MockModem()
        dimmer = Dimmer(modem.protocol, modem, Address("11.22.33"), "Dimmer")
        modem.devices[str(dimmer.addr)] = dimmer
        device = modem.find(Address("aa.bb.cc"))
        modem.devices[device.label] = device
        scenes = Scenes.SceneManager(modem, None)
        scenes.data = [{'controllers': [{'aa.bb.cc': {'group': 22}}],
                        'responders': ['11.22.33']},
                       {'controllers': [{'aa.bb.cc': {'group': 33}}],
                        'responders': ['11.22.33']}]
        scenes._init_scene_entries()
        entry1 = DeviceEntry.from_json({"addr": "aa.bb.cc",
                                        "group": 22,
                                        "mem_loc" : 8119,
                                        "db_flags": {"is_last_rec": False,
                                                     "in_use": True,
                                                     "is_controller": False},
                                        "data": [255, 23, 0]})
        scenes.add_or_update(dimmer, entry1)
        entry2 = DeviceEntry.from_json({"addr": "aa.bb.cc",
                                        "group": 33,
                                        "mem_loc" : 8119,
                                        "db_flags": {"is_last_rec": False,
                                                     "in_use": True,
                                                     "is_controller": False},
                                        "data": [255, 23, 0]})
        scenes.add_or_update(dimmer, entry2)
        scenes.compress_controllers()
        print(str(scenes.data))
        # We should end up with a single scene with:
        # - 2 controller entries: aa.bb.cc, group 22, group 23
        # - 1 responder entry: 11.22.33, ramp_rate 19 seconds
        assert len(scenes.entries) == 1
        assert len(scenes.data[0]['controllers']) == 2
        assert len(scenes.data[0]['responders']) == 1
        assert scenes.data[0]['responders'][0]['Dimmer']['ramp_rate'] == 19

    def test_Dimmer_scenes_different_ramp_rates(self):
        modem = MockModem()
        dimmer = Dimmer(modem.protocol, modem, Address("11.22.33"), "Dimmer")
        modem.devices[str(dimmer.addr)] = dimmer
        device = modem.find(Address("aa.bb.cc"))
        modem.devices[device.label] = device
        scenes = Scenes.SceneManager(modem, None)
        scenes.data = [{'controllers': [{'aa.bb.cc': {'group': 22}}],
                        'responders': ['11.22.33']},
                       {'controllers': [{'aa.bb.cc': {'group': 33}}],
                        'responders': ['11.22.33']}]
        scenes._init_scene_entries()
        entry1 = DeviceEntry.from_json({"addr": "aa.bb.cc",
                                        "group": 22,
                                        "mem_loc" : 8119,
                                        "db_flags": {"is_last_rec": False,
                                                     "in_use": True,
                                                     "is_controller": False},
                                        "data": [255, 23, 0]})
        scenes.add_or_update(dimmer, entry1)
        entry2 = DeviceEntry.from_json({"addr": "aa.bb.cc",
                                        "group": 33,
                                        "mem_loc" : 8119,
                                        "db_flags": {"is_last_rec": False,
                                                     "in_use": True,
                                                     "is_controller": False},
                                        "data": [255, 13, 0]})
        scenes.add_or_update(dimmer, entry2)
        scenes.compress_controllers()
        print(str(scenes.data))
        # We should end up with 2 scenes:
        # - Controller aa.bb.cc, group 22 -> Dimmer w/ 19 second ramp_rate
        # - Controller aa.bb.cc, group 33 -> Dimmer w/ 47 second ramp_rate
        # (Just checking # of scenes should be adequate for this test.)
        assert len(scenes.entries) == 2

    def test_FanLinc_scenes_same_ramp_rate(self):
        modem = MockModem()
        fanlinc = FanLinc(modem.protocol, modem, Address("11.22.33"), "FanLinc")
        modem.devices[str(fanlinc.addr)] = fanlinc
        device = modem.find(Address("aa.bb.cc"))
        modem.devices[device.label] = device
        scenes = Scenes.SceneManager(modem, None)
        scenes.data = [{'controllers': [{'aa.bb.cc': {'group': 22}}],
                        'responders': ['11.22.33']},
                       {'controllers': [{'aa.bb.cc': {'group': 33}}],
                        'responders': ['11.22.33']}]
        scenes._init_scene_entries()
        entry1 = DeviceEntry.from_json({"addr": "aa.bb.cc",
                                        "group": 22,
                                        "mem_loc" : 8119,
                                        "db_flags": {"is_last_rec": False,
                                                     "in_use": True,
                                                     "is_controller": False},
                                        "data": [255, 23, 1]})
        scenes.add_or_update(fanlinc, entry1)
        entry2 = DeviceEntry.from_json({"addr": "aa.bb.cc",
                                        "group": 33,
                                        "mem_loc" : 8119,
                                        "db_flags": {"is_last_rec": False,
                                                     "in_use": True,
                                                     "is_controller": False},
                                        "data": [255, 23, 1]})
        scenes.add_or_update(fanlinc, entry2)
        scenes.compress_controllers()
        print(str(scenes.data))
        # We should end up with a single scene with:
        # - 2 controller entries: aa.bb.cc, group 22, group 23
        # - 1 responder entry: 11.22.33, ramp_rate 19 seconds
        assert len(scenes.entries) == 1
        assert len(scenes.data[0]['controllers']) == 2
        assert len(scenes.data[0]['responders']) == 1
        assert scenes.data[0]['responders'][0]['FanLinc']['ramp_rate'] == 19

    def test_FanLinc_scenes_different_ramp_rates(self):
        modem = MockModem()
        fanlinc = FanLinc(modem.protocol, modem, Address("11.22.33"), "FanLinc")
        modem.devices[str(fanlinc.addr)] = fanlinc
        device = modem.find(Address("aa.bb.cc"))
        modem.devices[device.label] = device
        scenes = Scenes.SceneManager(modem, None)
        scenes.data = [{'controllers': [{'aa.bb.cc': {'group': 22}}],
                        'responders': ['11.22.33']},
                       {'controllers': [{'aa.bb.cc': {'group': 33}}],
                        'responders': ['11.22.33']}]
        scenes._init_scene_entries()
        entry1 = DeviceEntry.from_json({"addr": "aa.bb.cc",
                                        "group": 22,
                                        "mem_loc" : 8119,
                                        "db_flags": {"is_last_rec": False,
                                                     "in_use": True,
                                                     "is_controller": False},
                                        "data": [255, 23, 1]})
        scenes.add_or_update(fanlinc, entry1)
        entry2 = DeviceEntry.from_json({"addr": "aa.bb.cc",
                                        "group": 33,
                                        "mem_loc" : 8119,
                                        "db_flags": {"is_last_rec": False,
                                                     "in_use": True,
                                                     "is_controller": False},
                                        "data": [255, 13, 1]})
        scenes.add_or_update(fanlinc, entry2)
        scenes.compress_controllers()
        print(str(scenes.data))
        # We should end up with 2 scenes:
        # - Controller aa.bb.cc, group 22 -> FanLinc w/ 19 second ramp_rate
        # - Controller aa.bb.cc, group 33 -> FanLinc w/ 47 second ramp_rate
        # (Just checking # of scenes should be adequate for this test.)
        assert len(scenes.entries) == 2

    def test_KeypadLinc_scenes_same_ramp_rate(self):
        modem = MockModem()
        keypadlinc = KeypadLinc(modem.protocol, modem, Address("11.22.33"),
                                "KeypadLinc")
        modem.devices[str(keypadlinc.addr)] = keypadlinc
        device = modem.find(Address("aa.bb.cc"))
        modem.devices[device.label] = device
        scenes = Scenes.SceneManager(modem, None)
        scenes.data = [{'controllers': [{'aa.bb.cc': {'group': 22}}],
                        'responders': ['11.22.33']},
                       {'controllers': [{'aa.bb.cc': {'group': 33}}],
                        'responders': ['11.22.33']}]
        scenes._init_scene_entries()
        entry1 = DeviceEntry.from_json({"addr": "aa.bb.cc",
                                        "group": 22,
                                        "mem_loc" : 8119,
                                        "db_flags": {"is_last_rec": False,
                                                     "in_use": True,
                                                     "is_controller": False},
                                        "data": [255, 23, 1]})
        scenes.add_or_update(keypadlinc, entry1)
        entry2 = DeviceEntry.from_json({"addr": "aa.bb.cc",
                                        "group": 33,
                                        "mem_loc" : 8119,
                                        "db_flags": {"is_last_rec": False,
                                                     "in_use": True,
                                                     "is_controller": False},
                                        "data": [255, 23, 1]})
        scenes.add_or_update(keypadlinc, entry2)
        scenes.compress_controllers()
        print(str(scenes.data))
        # We should end up with a single scene with:
        # - 2 controller entries: aa.bb.cc, group 22, group 23
        # - 1 responder entry: 11.22.33, ramp_rate 19 seconds
        assert len(scenes.entries) == 1
        assert len(scenes.data[0]['controllers']) == 2
        assert len(scenes.data[0]['responders']) == 1
        assert scenes.data[0]['responders'][0]['KeypadLinc']['ramp_rate'] == 19

    def test_KeypadLinc_scenes_different_ramp_rates(self):
        modem = MockModem()
        keypadlinc = KeypadLinc(modem.protocol, modem, Address("11.22.33"),
                                "KeypadLinc")
        modem.devices[str(keypadlinc.addr)] = keypadlinc
        device = modem.find(Address("aa.bb.cc"))
        modem.devices[device.label] = device
        scenes = Scenes.SceneManager(modem, None)
        scenes.data = [{'controllers': [{'aa.bb.cc': {'group': 22}}],
                        'responders': ['11.22.33']},
                       {'controllers': [{'aa.bb.cc': {'group': 33}}],
                        'responders': ['11.22.33']}]
        scenes._init_scene_entries()
        entry1 = DeviceEntry.from_json({"addr": "aa.bb.cc",
                                        "group": 22,
                                        "mem_loc" : 8119,
                                        "db_flags": {"is_last_rec": False,
                                                     "in_use": True,
                                                     "is_controller": False},
                                        "data": [255, 23, 1]})
        scenes.add_or_update(keypadlinc, entry1)
        entry2 = DeviceEntry.from_json({"addr": "aa.bb.cc",
                                        "group": 33,
                                        "mem_loc" : 8119,
                                        "db_flags": {"is_last_rec": False,
                                                     "in_use": True,
                                                     "is_controller": False},
                                        "data": [255, 13, 1]})
        scenes.add_or_update(keypadlinc, entry2)
        scenes.compress_controllers()
        print(str(scenes.data))
        # We should end up with 2 scenes:
        # - Controller aa.bb.cc, group 22 -> KeypadLinc w/ 19 second ramp_rate
        # - Controller aa.bb.cc, group 33 -> KeypadLinc w/ 47 second ramp_rate
        # (Just checking # of scenes should be adequate for this test.)
        assert len(scenes.entries) == 2

    def test_foreign_hub_group_0(self):
        modem = MockModem()
        device = modem.find(Address("aa.bb.cc"))
        modem.devices[device.label] = device
        scenes = Scenes.SceneManager(modem, None)
        # We'll build the following via DeviceEntrys:
        #scenes.data = [{'controllers': [{'aa.bb.cc': 0}],
        #                'responders': ['cc.bb.22', 'cc.bb.aa']}]
        scenes._init_scene_entries()
        entry = DeviceEntry.from_json({"data": [3, 0, 239],
                                       "mem_loc" : 8119,
                                       "group": 0,
                                       "db_flags": {"is_last_rec": False,
                                                    "in_use": True,
                                                    "is_controller": False},
                                       "addr": "aa.bb.cc"})
        device = modem.find("cc.bb.22")
        scenes.add_or_update(device, entry)
        device = modem.find("cc.bb.aa")
        scenes.add_or_update(device, entry)
        print(str(scenes.data))
        # Check that group == 0
        assert scenes.entries[0].controllers[0].group == 0
        assert scenes.entries[0].controllers[0].style == 1
        assert scenes.data[0]['controllers'][0]['dev - aa.bb.cc'] == 0

    def test_foreign_hub_set_group_0(self):
        modem = MockModem()
        scenes = Scenes.SceneManager(modem, None)
        scenes.data = [{'controllers': [{'a1.b1.c1': {'data_1': 0}}],
                        'responders': ['cc.bb.22'],
                        'name': 'test'}]
        scenes._init_scene_entries()
        scenes.entries[0].controllers[0].group = 0
        print(str(scenes.data))
        assert scenes.data[0]['controllers'][0]['dev - a1.b1.c1']['group'] == 0

    def test_foreign_hub_group_0_and_1(self):
        modem = MockModem()
        device = modem.find(Address("aa.bb.cc"))
        modem.devices[device.label] = device
        scenes = Scenes.SceneManager(modem, None)
        # We'll build the following via DeviceEntrys:
        #scenes.data = [{'controllers': [{'aa.bb.cc': 0}, 'aa.bb.cc'],
        #                'responders': ['cc.bb.aa']}]
        scenes._init_scene_entries()
        entry1 = DeviceEntry.from_json({"data": [3, 0, 239],
                                        "mem_loc" : 8119,
                                        "group": 1,
                                        "db_flags": {"is_last_rec": False,
                                                     "in_use": True,
                                                     "is_controller": False},
                                        "addr": "aa.bb.cc"})
        device = modem.find("cc.bb.aa")
        scenes.add_or_update(device, entry1)
        entry2 = DeviceEntry.from_json({"data": [3, 0, 239],
                                        "mem_loc" : 8119,
                                        "group": 0,
                                        "db_flags": {"is_last_rec": False,
                                                     "in_use": True,
                                                     "is_controller": False},
                                        "addr": "aa.bb.cc"})
        device = modem.find("cc.bb.aa")
        scenes.add_or_update(device, entry2)
        scenes.compress_controllers()
        print(str(scenes.data))
        # Check that we have two controller entries & 1 responder
        assert len(scenes.entries) == 1
        assert len(scenes.data[0]['controllers']) == 2
        assert len(scenes.data[0]['responders']) == 1

    def test_mini_remote_button_config_no_data3(self):
        modem = MockModem()
        remote = Remote(modem.protocol, modem, Address("11.22.33"), "Remote", 4)
        modem.devices[str(remote.addr)] = remote
        device = modem.find(Address("aa.bb.cc"))
        modem.devices[device.label] = device
        scenes = Scenes.SceneManager(modem, None)
        # We'll build the following via DeviceEntrys:
        #scenes.data = [{'controllers': [{'11.22.33': 2}],
        #                'responders': ['aa.bb.cc']}]
        scenes._init_scene_entries()
        # The following data values are taken from an actual Mini Remote
        entry = DeviceEntry.from_json({"addr": "aa.bb.cc",
                                       "group": 2,
                                       "mem_loc" : 8119,
                                       "db_flags": {"is_last_rec": False,
                                                    "in_use": True,
                                                    "is_controller": True},
                                       "data": [3, 0, 0]})
        scenes.add_or_update(remote, entry)
        print(str(scenes.data))
        # We should end up with a single scene with:
        # - 1 controller entry: 11.22.33, group 2 (no data_3 value)
        # - 1 responder entry: aa.bb.cc
        assert len(scenes.entries) == 1
        assert len(scenes.data[0]['controllers']) == 1
        assert len(scenes.data[0]['responders']) == 1
        assert scenes.entries[0].controllers[0].group == 2
        assert scenes.entries[0].controllers[0].link_data == [3, 0, 0]
        assert scenes.entries[0].controllers[0].style == 1

    def test_mini_remote_button_config_with_data3(self):
        modem = MockModem()
        remote = Remote(modem.protocol, modem, Address("11.22.33"), "Remote", 4)
        modem.devices[str(remote.addr)] = remote
        device = modem.find(Address("aa.bb.cc"))
        modem.devices[device.label] = device
        scenes = Scenes.SceneManager(modem, None)
        # We'll build the following via DeviceEntrys:
        #scenes.data = [{'controllers': [{'11.22.33': {group: 2, data_3: 2}],
        #                'responders': ['aa.bb.cc']}]
        scenes._init_scene_entries()
        # Preserve data_3 values if present
        entry = DeviceEntry.from_json({"addr": "aa.bb.cc",
                                       "group": 2,
                                       "mem_loc" : 8119,
                                       "db_flags": {"is_last_rec": False,
                                                    "in_use": True,
                                                    "is_controller": True},
                                       "data": [3, 0, 2]})
        scenes.add_or_update(remote, entry)
        print(str(scenes.data))
        # We should end up with a single scene with:
        # - 1 controller entry: 11.22.33, group 2, data_3 = 2
        # - 1 responder entry: aa.bb.cc
        assert len(scenes.entries) == 1
        assert len(scenes.data[0]['controllers']) == 1
        assert len(scenes.data[0]['responders']) == 1
        assert scenes.entries[0].controllers[0].group == 2
        assert scenes.entries[0].controllers[0].link_data == [3, 0, 2]
        assert scenes.entries[0].controllers[0].style == 0
        assert scenes.data[0]['controllers'][0]['Remote']['group'] == 2
        assert scenes.data[0]['controllers'][0]['Remote']['data_3'] == 2

class MockModem():
    def __init__(self):
        self.save_path = ''
        self.devices = {}
        self.protocol = MockProto()
        self.devices['ff.ff.ff'] = self
        self.addr = Address("ff.ff.ff")
        self.name = 'modem'
        self.db = ModemDB(None, self)

    def type(self):
        return "Modem"

    def clear_db_config(self):
        pass

    def find(self, addr):
        if str(addr) not in self.devices:
            name = 'dev - ' + str(addr)
            device = Base(self.protocol, self, addr, name=name)
            self.devices[str(addr)] = device
        else:
            device = self.devices[str(addr)]
        return device

    def link_data(self, is_controller, group, data=None):
        if is_controller:
            defaults = [group, 0x00, 0x00]
        else:
            defaults = [group, 0x00, 0x00]
        return defaults

    def link_data_to_pretty(self, is_controller, data):
        return [{'data_1': data[0]}, {'data_2': data[1]}, {'data_3': data[2]}]

class MockProto:
    def __init__(self):
        self.msgs = []

    def send(self, msg, handler, high_priority=False, after=None):
        self.msgs.append(msg)

#===========================================================================
