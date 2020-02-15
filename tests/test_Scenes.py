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
        scenes._compress_scenes()
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
