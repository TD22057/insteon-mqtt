#===========================================================================
#
# Tests for: insteont_mqtt/Signal.py
#
#===========================================================================
import insteon_mqtt as IM
from pytest import assume

#===========================================================================
class Slot:
    static_data = []
    method_data = []

    @staticmethod
    def static_slot(**kwargs):
        Slot.static_data.append(kwargs)

    def method_slot(self, **kwargs):
        Slot.method_data.append(kwargs)

func_data = []
def func_slot(**kwargs):
    func_data.append(kwargs)

def clear():
    global func_data
    func_data = []
    Slot.static_data = []
    Slot.method_data = []

#===========================================================================
def test_func():
    clear()
    sig = IM.Signal()
    sig.connect(func_slot)

    sig.emit(a=1, b=2)

    assert len(func_data) == 1
    assert func_data[0] == {'a' : 1, 'b': 2}

#===========================================================================
def test_static():
    clear()
    sig = IM.Signal()
    sig.connect(Slot.static_slot)

    sig.emit(a=1, b=2)

    assert len(Slot.static_data) == 1
    assert Slot.static_data[0] == {'a' : 1, 'b': 2}

#===========================================================================
def test_method():
    clear()
    sig = IM.Signal()
    obj = Slot()
    sig.connect(obj.method_slot)

    sig.emit(a=1, b=2)

    assert len(Slot.method_data) == 1
    assert Slot.method_data[0] == {'a' : 1, 'b': 2}

#===========================================================================
def test_multi():
    clear()
    sig = IM.Signal()
    obj = Slot()
    sig.connect(obj.method_slot)
    sig.connect(Slot.static_slot)
    sig.connect(func_slot)

    sig.emit(a=1, b=2)
    sig.emit(c=3, d=4)

    assert len(Slot.method_data) == 2
    assert Slot.method_data[0] == {'a' : 1, 'b': 2}
    assert Slot.method_data[1] == {'c' : 3, 'd': 4}

    assert len(Slot.static_data) == 2
    assert Slot.static_data[0] == {'a' : 1, 'b': 2}
    assert Slot.static_data[1] == {'c' : 3, 'd': 4}

    assert len(func_data) == 2
    assert func_data[0] == {'a' : 1, 'b': 2}
    assert func_data[1] == {'c' : 3, 'd': 4}

    sig.disconnect(obj.method_slot)
    sig.emit(a=10)
    assert len(Slot.method_data) == 2
    assert len(Slot.static_data) == 3
    assert len(func_data) == 3

    sig.disconnect(obj.static_slot)
    sig.emit(a=10)
    assert len(Slot.method_data) == 2
    assert len(Slot.static_data) == 3
    assert len(func_data) == 4

    sig.disconnect(func_slot)
    sig.emit(a=10)
    assert len(Slot.method_data) == 2
    assert len(Slot.static_data) == 3
    assert len(func_data) == 4


#===========================================================================
def test_clear():
    clear()
    sig = IM.Signal()
    obj = Slot()
    sig.connect(obj.method_slot)
    sig.connect(Slot.static_slot)
    sig.connect(func_slot)

    sig.clear()
    sig.emit(a=1, b=2)
    assert len(Slot.method_data) == 0
    assert len(Slot.static_data) == 0
    assert len(func_data) == 0

#===========================================================================
def test_weakref():
    clear()
    sig = IM.Signal()
    obj = Slot()
    sig.connect(obj.method_slot)
    sig.connect(func_slot)

    del obj

    sig.emit(a=1, b=2)
    assert len(Slot.method_data) == 0
    assert len(func_data) == 1

#===========================================================================
def test_disconnect():
    clear()
    sig = IM.Signal()

    def dslot1(**kwargs):
        sig.disconnect(dslot1)
    def dslot2(**kwargs):
        sig.disconnect(dslot2)

    sig.connect(dslot1)
    sig.connect(func_slot)
    sig.connect(dslot2)

    sig.emit(a=1, b=2)
    assert len(func_data) == 1

    sig.disconnect(dslot1)


#===========================================================================
