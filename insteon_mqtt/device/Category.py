#===========================================================================
#
# Insteon Device Category
#
#===========================================================================
import enum

class Category(enum.IntEnum):
    CONTROLLERS = 0x00
    DIMMABLE_LIGHTING = 0x01
    SWITCHED_LIGHTING = 0x02
    NETWORK_BRIDGES = 0x03
    IRRIGATION = 0x04
    CLIMATE = 0x05
    POOL_SPA = 0x06
    SENSORS_ACTUATORS = 0x07
    HOME_ENTERTAINMENT = 0x08
    ENERGY = 0x09
    APPLIANCE = 0x0A
    PLUMBING = 0x0B
    COMMUNICATION = 0x0C
    COMPUTER = 0x0D
    WINDOW_COVERINGS = 0x0E
    ACCESS = 0x0F
    SECURITY_HEALTH_SAFETY = 0x10
    SURVEILLANCE = 0x11
    AUTOMOTIVE = 0x12
    PET_CARE = 0x13
    TOYS = 0x14
    TIMEKEEPING = 0x15
    HOLIDAY = 0x16
    UNASSIGNED = 0xFF

    @classmethod
    def _missing_(cls, value):
        for item in cls:
            if item.value == value:
                return item
        obj = int.__new__(cls)
        obj._value_ = value
        obj._name_ = "Unknown"
        return obj

    def __str__(self):
        return "%s" %(self.name)
