#===========================================================================
#
# Insteon product catalog
#
#===========================================================================
import enum
import collections

__doc__ = """Product device category information.

This module translates Insteon device category and sub-category integers into
strings.  It is most likely not complete.  It's only used for information
purposes so that should be fine.
"""

# Model string to use for unknown devices.
MODEL_UNKNOWN = "Unknown"


class Entry:
    """Device entry.

    This contains the device catalog ID, sub catalog ID, model string, and
    description string and is returned for a device using the find()
    function.  If the category is known, it will be a catalog.Cateogry
    enumeration, otherwise it's an integer.
    """
    def __init__(self, dev_cat, sub_cat, model=None, description=None):
        """Constructor

        Args:
          dev_cat (int):  The device category ID.
          sub_cat (int):  The device sub-category ID.
          model (str):  Optional model identification string.
          description (str):  Optional additional description.
        """
        # Try and turn an integer into a Category enumeration.
        try:
            dev_cat = Category(dev_cat)
        except:
            pass

        self.dev_cat = dev_cat
        self.sub_cat = sub_cat
        self.model = model
        self.description = description

    def __str__(self):
        if isinstance(self.dev_cat, Category):
            s = "%s (0x%0.2x): " % (self.dev_cat.name, int(self.dev_cat))
        else:
            s = "0x%0.2x: " % (self.dev_cat)

        if self.model:
            s += "'%s' (0x%0.2x)" % (self.model, self.sub_cat)
        else:
            s += "0x%0.2x" % (self.sub_cat)

        if self.description:
            s += " '%s'" % self.description

        return s


#===========================================================================
def exists(dev_cat, sub_cat):
    """See if an entry exists.

    Args:
      dev_cat (int):  The device category ID.
      sub_cat (int):  The device sub-category ID.

    Returns:
      (bool): Returns True if the inputs exist in the catalog.
    """
    entry = find(dev_cat, sub_cat)
    return entry.model != MODEL_UNKNOWN


#===========================================================================
def find(dev_cat, sub_cat, default=MODEL_UNKNOWN):
    """Find an Entry object for a device.

    If an entry doesn't exist and defaul

    Args:
      dev_cat (int):  The device category ID.
      sub_cat (int):  The device sub-category ID.
      default (str):  The default model string to use.  If this is None and
         the device is not found, a ValueError is raised.

    Returns:
      (Entry): Returns the requested Entry object.
    """
    sub_entries = entries.get(dev_cat, None)
    if sub_entries is not None:
        desc = sub_entries.get(sub_cat, None)

        # Found a matching entry.  Turn the data into an Entry object.
        if desc is not None:
            return Entry(dev_cat, sub_cat, desc.model, desc.desc)

    # If we have a default, use that to make an Entry object.
    if default is not None:
        return Entry(dev_cat, sub_cat, default, "")

    raise ValueError("Unknown device dev_cat=%s sub_cat=%s" %
                     (hex(dev_cat), hex(sub_cat)))


#===========================================================================
def find_all(dev_cat):
    """Find all the entries for a category.

    Args:
      dev_cat (int):  The device category ID.

    Returns:
      ([Entry]): Returns a list of the known entries for the input category.
    """
    results = []
    sub_entries = entries.get(dev_cat, None)
    if sub_entries is not None:
        for sub_cat, desc in sub_entries.items():
            results.append(Entry(dev_cat, sub_cat, desc.model, desc.desc))

    return results


#===========================================================================

# Struct to store the model and description strings.
Desc = collections.namedtuple('Desc', ['model', 'desc'])


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
    APPLIANCE = 0x0a
    PLUMBING = 0x0b
    COMMUNICATION = 0x0c
    COMPUTER = 0x0d
    WINDOW_COVERINGS = 0x0e
    ACCESS = 0x0f
    SECURITY_HEALTH_SAFETY = 0x10
    SURVEILLANCE = 0x11
    AUTOMOTIVE = 0x12
    PET_CARE = 0x13
    TOYS = 0x14
    TIMEKEEPING = 0x15
    HOLIDAY = 0x16


# Known device entry catalog.  This is NOT complete.  It's intended to help
# with descriptions for devices and possible future auto-discovery.
# Structure is: entries[dev_cat][sub_cat]
entries = {
    # dev_cat = 0x00
    Category.CONTROLLERS: {
        0x04: Desc("2430", "ControlLinc"),
        0x05: Desc("2440", "RemoteLinc"),
        0x06: Desc("2830", "ICON Tabletop Controller"),
        0x09: Desc("2442", "SignaLinc RF Signal Enhancer"),
        0x0a: Desc("N/A", "Poolux LCD Controller"),
        0x0b: Desc("2443", "Access Point (Wireless Phase Coupler)"),
        0x0C: Desc("12005", "IES Color Touchscreen"),
        0x0e: Desc("2440EZ", "RemoteLinc EZ"),
        0x10: Desc("2444A2xx4", "RemoteLinc 2 Keypad, 4 Scene"),
        0x11: Desc("2444A3xx", "RemoteLinc 2 Switch"),
        0x12: Desc("2444A2xx8", "RemoteLinc 2 Keypad, 8 Scene"),
        0x13: Desc("2993-222", "Insteon Diagnostics Keypad"),
        0x14: Desc("2342-432", "Insteon Mini Remote - 4 Scene (869 MHz)"),
        0x15: Desc("2342-442", "Insteon Mini Remote - Switch (869 MHz)"),
        0x16: Desc("2342-422", "Insteon Mini Remote - 8 Scene (869 MHz)"),
        0x17: Desc("2342-532", "Insteon Mini Remote - 4 Scene (921 MHz)"),
        0x18: Desc("2342-522", "Insteon Mini Remote - 8 Scene (921 MHz)"),
        0x19: Desc("2342-542", "Insteon Mini Remote - Switch (921 MHz)"),
        0x1a: Desc("2342-222", "Insteon Mini Remote - 8 Scene (915 MHz)"),
        0x1b: Desc("2342-232", "Insteon Mini Remote - 4 Scene (915 MHz)"),
        0x1c: Desc("2342-242", "Insteon Mini Remote - Switch (915 MHz)"),
        0x1d: Desc("2992-222", "Range Extender"),
        },
    # dev_cat = 0x01
    Category.DIMMABLE_LIGHTING : {
        0x00: Desc("2456D3", "LampLinc 3-Pin"),
        0x01: Desc("2476D", "SwitchLinc Dimmer"),
        0x02: Desc("2475D", "In-LineLinc Dimmer"),
        0x03: Desc("2876DB", "ICON Dimmer Switch"),
        0x04: Desc("2476DH", "SwitchLinc Dimmer (High Wattage)"),
        0x05: Desc("2484DWH8", "Keypad Countdown Timer w/ Dimmer"),
        0x06: Desc("2456D2", "LampLinc Dimmer (2-Pin)"),
        0x07: Desc("2856D2B", "ICON LampLinc"),
        0x08: Desc("2476DT", "SwitchLinc Dimmer Count-down Timer"),
        0x09: Desc("2486D", "KeypadLinc Dimmer"),
        0x0a: Desc("2886D", "Icon In-Wall Controller"),
        0x0b: Desc("2632-422", "Insteon Dimmer Module, France (869 MHz)"),
        0x0c: Desc("2486DWH8", "KeypadLinc Dimmer"),
        0x0d: Desc("2454D", "SocketLinc"),
        0x0e: Desc("2457D2", "LampLinc (Dual-Band)"),
        0x0f: Desc("2632-432", "Insteon Dimmer Module, Germany (869 MHz)"),
        0x11: Desc("2632-442", "Insteon Dimmer Module, UK (869 MHz)"),
        0x12: Desc("2632-522", "Insteon Dimmer Module, Aus/NZ (921 MHz)"),
        0x13: Desc("2676D-B", "ICON SwitchLinc Dimmer Lixar/Bell Canada"),
        0x17: Desc("2466D", "ToggleLinc Dimmer"),
        0x18: Desc("2474D", "Icon SwitchLinc Dimmer Inline Companion"),
        0x19: Desc("2476D", "SwitchLinc Dimmer [with beeper]"),
        0x1a: Desc("2475D", "In-LineLinc Dimmer [with beeper]"),
        0x1b: Desc("2486DWH6", "KeypadLinc Dimmer"),
        0x1c: Desc("2486DWH8", "KeypadLinc Dimmer"),
        0x1d: Desc("2476DH", "SwitchLinc Dimmer (High Wattage)[beeper]"),
        0x1e: Desc("2876DB", "ICON Switch Dimmer"),
        0x1f: Desc("2466Dx", "ToggleLinc Dimmer [with beeper]"),
        0x20: Desc("2477D", "SwitchLinc Dimmer (Dual-Band)"),
        0x21: Desc("2472D", "OutletLinc Dimmer (Dual-Band)"),
        0x22: Desc("2457D2X", "LampLinc"),
        0x23: Desc("2457D2EZ", "LampLinc Dual-Band EZ"),
        0x24: Desc("2474DWH", "SwitchLinc 2-Wire Dimmer (RF)"),
        0x25: Desc("2475DA2", "In-LineLinc 0-10VDC Dimmer/Dual-SwitchDB"),
        0x2d: Desc("2477DH", "SwitchLinc-Dimmer Dual-Band 1000W"),
        0x2e: Desc("2475F", "FanLinc"),
        0x2f: Desc("2484DST6", "KeypadLinc Schedule Timer with Dimmer"),
        0x30: Desc("2476D", "SwitchLinc Dimmer"),
        0x31: Desc("2478D", "SwitchLinc Dimmer 240V-50/60Hz Dual-Band"),
        0x32: Desc("2475DA1", "In-LineLinc Dimmer (Dual Band)"),
        0x34: Desc("2452-222", "Insteon DIN Rail Dimmer (915 MHz)"),
        0x35: Desc("2442-222", "Insteon Micro Dimmer (915 MHz)"),
        0x36: Desc("2452-422", "Insteon DIN Rail Dimmer (869 MHz)"),
        0x37: Desc("2452-522", "Insteon DIN Rail Dimmer (921 MHz)"),
        0x38: Desc("2442-422", "Insteon Micro Dimmer (869 MHz)"),
        0x39: Desc("2442-522", "Insteon Micro Dimmer (921 MHz)"),
        0x3a: Desc("2672-222", "LED Bulb 240V (915 MHz) - Screw-in Base"),
        0x3b: Desc("2672-422", "LED Bulb 240V Europe - Screw-in Base"),
        0x3c: Desc("2672-522", "LED Bulb 240V Aus/NZ - Screw-in Base"),
        0x3d: Desc("2446-422", "Insteon Ballast Dimmer (869 MHz)"),
        0x3e: Desc("2446-522", "Insteon Ballast Dimmer (921 MHz)"),
        0x3f: Desc("2447-422", "Insteon Fixture Dimmer (869 MHz)"),
        0x40: Desc("2447-522", "Insteon Fixture Dimmer (921 MHz)"),
        0x41: Desc("2334-222", "Keypad Dimmer Dual-Band, 8 Button"),
        0x42: Desc("2334-232", "Keypad Dimmer Dual-Band, 6 Button"),
        0x49: Desc("2674-222", "LED Bulb PAR38 US/Can - Screw-in Base"),
        0x4a: Desc("2674-422", "LED Bulb PAR38 Europe - Screw-in Base"),
        0x4b: Desc("2674-522", "LED Bulb PAR38 Aus/NZ - Screw-in Base"),
        0x4c: Desc("2672-432", "LED Bulb 240V Europe - Bayonet Base"),
        0x4d: Desc("2672-532", "LED Bulb 240V Aus/NZ - Bayonet Base"),
        0x4e: Desc("2674-432", "LED Bulb PAR38 Europe - Bayonet Base"),
        0x50: Desc("2632-452", "Insteon Dimmer Module, Chile (915 MHz)"),
        0x51: Desc("2672-452", "LED Bulb 240V (915 MHz) - Screw-in Base"),
        },
    # dev_cat = 0x02
    Category.SWITCHED_LIGHTING: {
        0x05: Desc("2486SWH8", "KeypadLinc 8-button On/Off Switch"),
        0x06: Desc("2456S3E", "Outdoor ApplianceLinc"),
        0x07: Desc("2456S3T", "TimerLinc"),
        0x08: Desc("2473S", "OutletLinc"),
        0x09: Desc("2456S3", "ApplianceLinc (3-Pin)"),
        0x0a: Desc("2476S", "SwitchLinc Relay"),
        0x0b: Desc("2876S", "ICON On/Off Switch"),
        0x0c: Desc("2856S3", "Icon Appliance Module"),
        0x0d: Desc("2466S", "ToggleLinc Relay"),
        0x0e: Desc("2476ST", "SwitchLinc Relay Countdown Timer"),
        0x0f: Desc("2486SWH6", "KeypadLinc On/Off"),
        0x10: Desc("2475S", "In-LineLinc Relay"),
        0x12: Desc("2474 S/D", "ICON In-lineLinc Relay Companion"),
        0x13: Desc("2676R-B", "ICON SwitchLinc Relay Lixar/Bell Canada"),
        0x14: Desc("2475S2", "In-LineLinc Relay with Sense"),
        0x15: Desc("2476SS", "SwitchLinc Relay with Sense"),
        0x16: Desc("2876S", "ICON On/Off Switch (25 max links)"),
        0x17: Desc("2856S3B", "ICON Appliance Module"),
        0x18: Desc("2494S220", "SwitchLinc 220V Relay"),
        0x19: Desc("2494S220", "SwitchLinc 220V Relay [with beeper]"),
        0x1a: Desc("2466Sx", "ToggleLinc Relay [with Beeper]"),
        0x1c: Desc("2476S", "SwitchLinc Relay"),
        0x1d: Desc("4101", "Commercial Switch with relay"),
        0x1e: Desc("2487S", "KeypadLinc On/Off (Dual-Band)"),
        0x1f: Desc("2475SDB", "In-LineLinc On/Off (Dual-Band)"),
        0x25: Desc("2484SWH8", ("KeypadLinc 8-Button Countdown On/Off "
                                "Switch Timer")),
        0x26: Desc("2485SWH6", "Keypad Schedule Timer with On/Off Switch"),
        0x29: Desc("2476ST", "SwitchLinc Relay Countdown Timer"),
        0x2a: Desc("2477S", "SwitchLinc Relay (Dual-Band)"),
        0x2b: Desc("2475SDB-50", "In-LineLinc On/Off (Dual Band, 50/60 Hz)"),
        0x2c: Desc("2487S", "KeypadLinc On/Off (Dual-Band,50/60 Hz)"),
        0x2d: Desc("2633-422", "Insteon On/Off Module, France (869 MHz)"),
        0x2e: Desc("2453-222", "Insteon DIN Rail On/Off (915 MHz)"),
        0x2f: Desc("2443-222", "Insteon Micro On/Off (915 MHz)"),
        0x30: Desc("2633-432", "Insteon On/Off Module, Germany (869 MHz)"),
        0x31: Desc("2443-422", "Insteon Micro On/Off (869 MHz)"),
        0x32: Desc("2443-522", "Insteon Micro On/Off (921 MHz)"),
        0x33: Desc("2453-422", "Insteon DIN Rail On/Off (869 MHz)"),
        0x34: Desc("2453-522", "Insteon DIN Rail On/Off (921 MHz)"),
        0x35: Desc("2633-442", "Insteon On/Off Module, UK (869 MHz)"),
        0x37: Desc("2635-222", "Insteon On/Off Module, US (915 MHz)"),
        0x38: Desc("2634-222", "On/Off Outdoor Module (Dual-Band)"),
        0x39: Desc("2663-222", "On/Off Outlet"),
        0x3A: Desc("2633-452", "Insteon On/Off Module, Chile (915 MHz)"),
        },
    # dev_cat = 0x03
    Category.NETWORK_BRIDGES: {
        0x01: Desc("2414S", "PowerLinc Serial Controller"),
        0x02: Desc("2414U", "PowerLinc USB Controller"),
        0x03: Desc("2814S", "ICON PowerLinc Serial"),
        0x04: Desc("2814U", "ICON PowerLinc USB"),
        0x05: Desc("2412S", "PowerLinc Serial Modem"),
        0x06: Desc("2411R", "IRLinc Receiver"),
        0x07: Desc("2411T", "IRLinc Transmitter"),
        0x09: Desc("2600RF", "SmartLabs RF Developer’s Board"),
        0x0a: Desc("2410S", "SeriaLinc - Insteon to RS232"),
        0x0b: Desc("2412U", "PowerLinc USB Modem"),
        0x0f: Desc("EZX10IR", "EZX10IR X10 IR Receiver"),
        0x10: Desc("2412N", "SmartLinc"),
        0x11: Desc("2413S", "PowerLinc Serial Modem (Dual Band)"),
        0x13: Desc("2412UH", "PowerLinc USB Modem for HouseLinc"),
        0x14: Desc("2412SH", "PowerLinc Serial Modem for HouseLinc"),
        0x15: Desc("2413U", "PowerLinc USB Modem (Dual Band)"),
        0x18: Desc("2243-222", "Insteon Central Controller (915 MHz)"),
        0x19: Desc("2413SH", "PowerLinc Serial Modem for HL(Dual Band)"),
        0x1a: Desc("2413UH", "PowerLinc USB Modem for HL (Dual Band)"),
        0x1b: Desc("2423A4", "iGateway"),
        0x1c: Desc("2423A7", "iGateway 2.0"),
        0x1e: Desc("2412S", "PowerLincModemSerial w/o EEPROM(w/o RF)"),
        0x1f: Desc("2448A7", "USB Adapter - Domestically made"),
        0x20: Desc("2448A7", "USB Adapter"),
        0x21: Desc("2448A7H", "Portable USB Adapter for HouseLinc"),
        0x23: Desc("2448A7H", "Portable USB Adapter for HouseLinc"),
        0x24: Desc("2448A7T", "TouchLinc"),
        0x27: Desc("2448A7T", "TouchLinc"),
        0x28: Desc("2413Gxx", "Global PLM, Dual Band (915 MHz)"),
        0x29: Desc("2413SAD", ("PowerLinc Serial Modem (Dual Band) RF OFF, "
                               "Auto Detect 128K")),
        0x2b: Desc("2242-222", "Insteon Hub (915 MHz) - no RF"),
        0x2e: Desc("2242-422", "Insteon Hub (EU - 869 MHz)"),
        0x2f: Desc("2242-522", "Insteon Hub (921 MHz)"),
        0x30: Desc("2242-442", "Insteon Hub (UK - 869 MHz)"),
        0x31: Desc("2242-232", "Insteon Hub (Plug-In Version)"),
        0x33: Desc("2245-222", "Insteon Hub II (915 MHz)"),
        0x37: Desc("2242-222", "Insteon Hub (915 MHz) - RF"),
        },
    # dev_cat = 0x04
    Category.IRRIGATION: {
        0x00: Desc("31270", "Compacta EZRain Sprinkler Controller"),
        0x02: Desc("2670IAQ-110", "Broan SMSC110 Exhaust Fan (no beeper)"),
        },
    # dev_cat = 0x05
    Category.CLIMATE: {
        0x03: Desc("2441V", "Thermostat Adapter"),
        0x07: Desc("2441ZT", "Insteon Wireless Thermostat"),
        0x0a: Desc("2441ZTH", "Insteon Wireless Thermostat (915 MHz)"),
        0x0b: Desc("2441TH", "Insteon Thermostat (915 MHz)"),
        0x0c: Desc("2670IAQ-80", "Broan SMSC080 Switch for 80CFM Fans"),
        0x0d: Desc("2670IAQ-110", "Broan SMSC110 Switch for 110CFM Fans"),
        0x0e: Desc("2491TxE", "Integrated Remote Control Thermostat"),
        0x0f: Desc("2732-422", "Insteon Thermostat (869 MHz)"),
        0x10: Desc("2732-522", "Insteon Thermostat (921 MHz)"),
        0x11: Desc("2732-432", "Insteon Zone Thermostat (869 MHz)"),
        0x12: Desc("2732-532", "Insteon Zone Thermostat (921 MHz)"),
        0x13: Desc("2732-242", "Heat Pump Thermostat - US/Can (915MHz)"),
        0x14: Desc("2732-242", "Heat Pump Thermostat - Europe (869.85MHz)"),
        0x15: Desc("2732-242", "Heat Pump Thermostat - Aus/NZ (921MHz)"),
        },
    # dev_cat = 0x06
    Category.POOL_SPA: {
        },
    # dev_cat = 0x07
    Category.SENSORS_ACTUATORS: {
        0x00: Desc("2450", "I/OLinc"),
        0x03: Desc("31274", "Compacta EZIO2X4 #5010D"),
        0x05: Desc("31275", "Compacta EZSnsRF RcvrIntrfc Dakota Alert"),
        0x07: Desc("31280", "EZIO6I (6 inputs)"),
        0x08: Desc("31283", "EZIO4O (4 relay outputs)"),
        0x09: Desc("2423A5", "SynchroLinc"),
        0x0c: Desc("2448A5", "Lumistat"),
        0x0d: Desc("2450", "I/OLinc 50/60Hz Auto Detect"),
        0x0e: Desc("2248-222", "I/O Module - US (915 MHz)"),
        0x0f: Desc("2248-422", "I/O Module - EU (869.85 MHz)"),
        0x10: Desc("2248-442", "I/O Module - UK (869.85 MHz)"),
        0x11: Desc("2248-522", "I/O Module - AUS (921 MHz)"),
        0x12: Desc("2822-222", "IOLinc Dual-Band - US"),
        0x13: Desc("2822-422", "IOLinc Dual-Band - EU"),
        0x14: Desc("2822-442", "IOLinc Dual-Band - UK"),
        0x15: Desc("2822-522", "IOLinc Dual-Band - AUS/NZ"),
        0x16: Desc("2822-222", ("Low Voltage/Contact Closure Interface "
                                "(Dual Band) - US")),
        0x17: Desc("2822-422", ("Low Voltage/Contact Closure Interface "
                                "(Dual Band) - EU")),
        0x18: Desc("2822-442", ("Low Voltage/Contact Closure Interface "
                                "(Dual Band) - UK")),
        0x19: Desc("2822-522", ("Low Voltage/Contact Closure Interface "
                                "(Dual Band) - AUS/NZ")),
        },
    # dev_cat = 0x08
    Category.HOME_ENTERTAINMENT: {
        },
    # dev_cat = 0x09
    Category.ENERGY: {
        0x07: Desc("2423A1", "iMeter Solo"),
        0x08: Desc("2423A2", "iMeter Home (Breaker Panel)"),
        0x09: Desc("2423A3", "iMeter Home (Meter)"),
        0x0a: Desc("2477SA1", "220/240V 30A Load Controller NO (DB)"),
        0x0b: Desc("2477SA2", "220/240V 30A Load Controller NC (DB)"),
        0x0c: Desc("2630A1", "GE Water Heater U-SNAP module"),
        0x0d: Desc("2448A2", "Energy Display"),
        0x11: Desc("2423A8", "Insteon Digital Meter Reader"),
        },
    # dev_cat = 0x0a
    Category.APPLIANCE: {
        },
    # dev_cat = 0x0b
    Category.PLUMBING: {
        },
    # dev_cat = 0x0c
    Category.COMMUNICATION: {
        },
    # dev_cat = 0x0d
    Category.COMPUTER: {
        },
    # dev_cat = 0x0e
    Category.WINDOW_COVERINGS: {
        0x00: Desc("318276I", "Somfy Drape Controller RF Bridge"),
        0x01: Desc("2444-222", "Insteon Micro Open/Close (915 MHz)"),
        0x02: Desc("2444-422", "Insteon Micro Open/Close (869 MHz)"),
        0x03: Desc("2444-522", "Insteon Micro Open/Close (921 MHz)"),
        0x04: Desc("2772-222", "Window Shade Kit - US"),
        0x05: Desc("2772-422", "Window Shade Kit - EU"),
        0x06: Desc("2772-522", "Window Shade Kit - AUS/NZ"),
        },
    # dev_cat = 0x0f
    Category.ACCESS: {
        0x06: Desc("2458A1", "MorningLinc"),
        },
    # dev_cat = 0x10
    Category.SECURITY_HEALTH_SAFETY: {
        0x01: Desc("2842-222", "Motion Sensor - US (915 MHz)"),
        0x02: Desc("2843-222", "Insteon Open/Close Sensor (915 MHz)"),
        0x04: Desc("2842-422", "Insteon Motion Sensor (869 MHz)"),
        0x05: Desc("2842-522", "Insteon Motion Sensor (921 MHz)"),
        0x06: Desc("2843-422", "Insteon Open/Close Sensor (869 MHz)"),
        0x07: Desc("2843-522", "Insteon Open/Close Sensor (921 MHz)"),
        0x08: Desc("2852-222", "Leak Sensor - US (915 MHz)"),
        0x09: Desc("2843-232", "Insteon Door Sensor"),
        0x0a: Desc("2982-222", "Smoke Bridge"),
        0x0d: Desc("2852-422", "Leak Sensor - EU (869 MHz)"),
        0x0e: Desc("2852-522", "Leak Sensor - AUS/NZ (921 MHz)"),
        0x11: Desc("2845-222", "Door Sensor II (915 MHz)"),
        0x14: Desc("2845-422", "Door Sensor II (869 MHz)"),
        0x15: Desc("2845-522", "Door Sensor II (921 MHz)"),
        0x16: Desc("2844-222", "Motion Sensor II - (915 MHz)"),
        },
    # dev_cat = 0x11
    Category.SURVEILLANCE: {
        },
    # dev_cat = 0x12
    Category.AUTOMOTIVE: {
        },
    # dev_cat = 0x13
    Category.PET_CARE: {
        },
    # dev_cat = 0x14
    Category.TOYS: {
        },
    # dev_cat = 0x15
    Category.TIMEKEEPING: {
        },
    # dev_cat = 0x16
    Category.HOLIDAY: {
        },
    }
