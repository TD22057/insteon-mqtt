#===========================================================================
#
# Insteon Product Keys
#
#===========================================================================
import enum
from .Category import Category

class Product(enum.Enum):

    # Generalized Controllers
    CONTROLLINC = 0x00, 0x04, None, "ControlLinc", "2430"
    REMOTELINC = 0x00, 0x05, 0x000034, "RemoteLinc", "2440"
    ICON_TABLETOP_CONTROLLER = 0x00, 0x06, None, "Icon Tabletop Controller", "2830"
    EZBRIDGEEZSERVER = 0x00, 0x08, 0x00003D, "EZBridge/EZServer", None
    SIGNALINC_RF_SIGNAL_ENHANCER = 0x00, 0x09, None, "SignaLinc RF Signal Enhancer", "2442"
    BALBOA_INSTRUMENTS_POOLUX_LCD_CONTROLLER = 0x00, 0x0A, 0x000007, "Balboa Instrument’s Poolux LCD Controller", None
    ACCESS_POINT = 0x00, 0x0B, 0x000022, "Access Point", "2443"
    IES_COLOR_TOUCHSCREEN = 0x00, 0x0C, 0x000028, "IES Color Touchscreen", None
    SMARTLABS_KEYFOB = 0x00, 0x0D, 0x00004D, "SmartLabs KeyFOB", None
    LAMPLINC_V2 = 0x01, 0x00, None, "LampLinc V2", "2456D3"
    SWITCHLINC_V2_DIMMER_600W = 0x01, 0x01, None, "SwitchLinc V2 Dimmer 600W", "2476D"

    # Dimmable Lighting Control
    INLINELINC_DIMMER = 0x01, 0x02, None, "In-LineLinc Dimmer", "2475D"
    ICON_SWITCH_DIMMER = 0x01, 0x03, None, "Icon Switch Dimmer", "2876D"
    SWITCHLINC_V2_DIMMER_1000W = 0x01, 0x04, None, "SwitchLinc V2 Dimmer 1000W", "2476DH"
    KEYPADLINC_DIMMER_COUNTDOWN_TIMER = 0x01, 0x05, 0x000041, "KeypadLinc Dimmer Countdown Timer", "2484DWH8"
    LAMPLINC_2PIN = 0x01, 0x06, None, "LampLinc 2-Pin", "2456D2"
    ICON_LAMPLINC_V2_2PIN = 0x01, 0x07, None, "Icon LampLinc V2 2-Pin", "2856D2"
    SWITCHLINC_DIMMER_COUNTDOWN_TIMER = 0x01, 0x08, 0x000040, "SwitchLinc Dimmer Count-down Timer", "2484DWH8"
    KEYPADLINC_DIMMER = 0x01, 0x09, 0x000037, "KeypadLinc Dimmer", "2486D"
    ICON_INWALL_CONTROLLER = 0x01, 0x0A, None, "Icon In-Wall Controller", "2886D"
    ACCESS_POINT_LAMPLINC = 0x01, 0x0B, 0x00001C, "Access Point LampLinc", "2458D3"
    KEYPADLINC_DIMMER_8BUTTON = 0x01, 0x0C, 0x00001D, "KeypadLinc Dimmer – 8-Button", "2486DWH8"
    SOCKETLINC = 0x01, 0x0D, 0x00001E, "SocketLinc", "2454D"
    LAMPLINC_DIMMER_DUALBAND = 0x01, 0x0E, 0x00004B, "LampLinc Dimmer, Dual-Band", "2457D3"
    ICON_SWITCHLINC_DIMMER_FOR_LIXARBELL_CANADA = 0x01, 0x13, 0x000032, "ICON SwitchLinc Dimmer for Lixar/Bell Canada", "2676D-B"
    TOGGLELINC_DIMMER = 0x01, 0x17, None, "ToggleLinc Dimmer", "2466D"
    ICON_SL_DIMMER_INLINE_COMPANION = 0x01, 0x18, 0x00003F, "Icon SL Dimmer Inline Companion", "2474D"
    SWITCHLINC_800W = 0x01, 0x19, 0x00004E, "SwitchLinc 800W", None
    INLINELINC_DIMMER_WITH_SENSE = 0x01, 0x1A, 0x00004F, "In-LineLinc Dimmer with Sense", "2475D2"
    KEYPADLINC_8BUTTON_DIMMER = 0x01, 0x1C, 0x000051, "KeypadLinc 8-button Dimmer", "2486DWH8"
    SWITCHLINC_DIMMER_1200W = 0x01, 0x1D, 0x000052, "SwitchLinc Dimmer 1200W", "2476D"

    # Switched Lighting Control
    KEYPADLINC_RELAY_8BUTTON = 0x02, 0x05, 0x000042, "KeypadLinc Relay – 8-Button", "2486SWH8"
    OUTDOOR_APPLIANCELINC = 0x02, 0x06, 0x000048, "Outdoor ApplianceLinc", "2456S3E"
    TIMERLINC = 0x02, 0x07, 0x000029, "TimerLinc", "2456ST3"
    OUTLETLINC = 0x02, 0x08, 0x000023, "OutletLinc", "2473S"
    APPLIANCELINC = 0x02, 0x09, None, "ApplianceLinc", "2456S3"
    SWITCHLINC_RELAY = 0x02, 0x0A, None, "SwitchLinc Relay", "2476S"
    ICON_ON_OFF_SWITCH = 0x02, 0x0B, None, "Icon On Off Switch", "2876S"
    ICON_APPLIANCE_ADAPTER = 0x02, 0x0C, None, "Icon Appliance Adapter", "2856S3"
    NAMTOGGLELINC_RELAYEz = 0x02, 0x0D, None, "ToggleLinc Relay", "2466S"
    SWITCHLINC_RELAY_COUNTDOWN_TIMER = 0x02, 0x0E, None, "SwitchLinc Relay Countdown Timer", "2476ST"
    KEYPADLINC_ONOFF_SWITCH = 0x02, 0x0F, 0x000036, "KeypadLinc On/Off Switch", "2486SWH6"
    INLINELINC_RELAY = 0x02, 0x10, 0x00001B, "In-LineLinc Relay", "2475D"
    EZSWITCH30_240V_30A_LOAD_CONTROLLER = 0x02, 0x11, 0x00003C, "EZSwitch30 (240V, 30A load controller)", None
    ICON_SL_RELAY_INLINE_COMPANION = 0x02, 0x12, 0x00003E, "Icon SL Relay Inline Companion", None
    ICON_SWITCHLINC_RELAY_FOR_LIXARBELL_CANADA = 0x02, 0x13, 0x000033, "ICON SwitchLinc Relay for Lixar/Bell Canada", "2676R-B"
    INLINELINC_RELAY_WITH_SENSE = 0x02, 0x14, 0x000045, "In-LineLinc Relay with Sense", "2475S2"
    SWITCHLINC_RELAY_WITH_SENSE = 0x02, 0x15, 0x000047, "SwitchLinc Relay with Sense", "2476S2"

    # Network Bridges
    POWERLINC_SERIAL = 0x03, 0x01, None, "PowerLinc Serial", "2414S"
    POWERLINC_USB = 0x03, 0x02, None, "PowerLinc USB", "2414U"
    ICON_POWERLINC_SERIAL = 0x03, 0x03, None, "Icon PowerLinc Serial", "2814 S"
    ICON_POWERLINC_USB = 0x03, 0x04, None, "Icon PowerLinc USB", "2814U"
    SMARTLABS_POWERLINC_MODEM_SERIAL = 0x03, 0x05, 0x00000C, "SmartLabs PowerLinc Modem Serial", "2412S"
    SMARTLABS_IR_TO_INSTEON_INTERFACE = 0x03, 0x06, 0x000016, "SmartLabs IR to Insteon Interface", "2411R"
    SMARTLABS_IRLINC_IR_TRANSMITTER_INTERFACE = 0x03, 0x07, 0x000017, "SmartLabs IRLinc - IR Transmitter Interface", "2411T"
    SMARTLABS_BIDIRECTIONAL_IR_INSTEON_INTERFACE = 0x03, 0x08, 0x000018, "SmartLabs Bi-Directional IR -Insteon Interface", None
    SMARTLABS_RF_DEVELOPERS_BOARD = 0x03, 0x09, 0x000019, "SmartLabs RF Developer’s Board", "2600RF"
    SMARTLABS_POWERLINC_MODEM_ETHERNET = 0x03, 0x0A, 0x00000D, "SmartLabs PowerLinc Modem Ethernet", "2412E"
    SMARTLABS_POWERLINC_MODEM_USB = 0x03, 0x0B, 0x000030, "SmartLabs PowerLinc Modem USB", "2412U"
    SMARTLABS_PLM_ALERT_SERIAL = 0x03, 0x0C, 0x000031, "SmartLabs PLM Alert Serial", None
    SIMPLEHOMENET_EZX10RF = 0x03, 0x0D, 0x000035, "SimpleHomeNet EZX10RF", None
    X10_TW523PSC05_TRANSLATOR = 0x03, 0x0E, 0x00002C, "X10 TW-523/PSC05 Translator", None
    EZX10IR_X10_IR_RECEIVER_INSTEON_CONTROLLER_AND_IR_DISTRIBUTION_HUB = 0x03, 0x0F, 0x00003B, "EZX10IR (X10 IR receiver, Insteon controller and IR distribution hub)", None
    SMARTLINC_2412N_INSTEON_CENTRAL_CONTROLLER = 0x03, 0x10, 0x000044, "SmartLinc 2412N INSTEON Central Controller", None
    POWERLINC_SERIAL_DUAL_BAND = 0x03, 0x11, 0x000045, "PowerLinc - Serial (Dual Band)", "2413S"
    RF_MODEM_CARD = 0x03, 0x12, 0x00004C, "RF Modem Card", None
    POWERLINC_USB_HOUSELINC_2 = 0x03, 0x13, 0x000053, "PowerLinc USB – HouseLinc 2", "2412UH"
    POWERLINC_SERIAL_HOUSELINC_2 = 0x03, 0x14, 0x000054, "PowerLinc Serial – HouseLinc 2", "2412SH"

    # Irrigation Control
    COMPACTA_EZRAIN_SPRINKLER_CONTROLLER = 0x04, 0x00, 0x000001, "Compacta EZRain Sprinkler Controller", None

    # Climate Control
    BROAN_SMSC080_EXHAUST_FAN = 0x05, 0x00, None, "Broan SMSC080 Exhaust Fan"
    COMPACTA_EZTHERM = 0x05, 0x01, 0x000002, "Compacta EZTherm", None
    BROAN_SMSC110_EXHAUST_FAN = 0x05, 0x02, None, "Broan SMSC110 Exhaust Fan", None
    INSTEON_THERMOSTAT_ADAPTER = 0x05, 0x03, 0x00001F, "INSTEON Thermostat Adapter", "2441V"
    COMPACTA_EZTHERMX_THERMOSTAT = 0x05, 0x04, 0x000024, "Compacta EZThermx Thermostat", None
    BROAN_VENMAR_BEST_RANGEHOODS = 0x05, 0x05, 0x000038, "Broan, Venmar, BEST Rangehoods", None
    BROAN_SMARTSENSE_MAKEUP_DAMPER = 0x05, 0x06, 0x000043, "Broan SmartSense Make-up Damper", None

    # Pool and Spa Control
    COMPACTA_EZPOOL = 0x06, 0x00, 0x000003, "Compacta EZPool", None
    LOWEND_POOL_CONTROLLER_TEMP_ENG_PROJECT_NAME = 0x06, 0x01, 0x000008, "Low-end pool controller (Temp. Eng. Project name)", None
    MIDRANGE_POOL_CONTROLLER_TEMP_ENG_PROJECT_NAME = 0x06, 0x02, 0x000009, "Mid-Range pool controller (Temp. Eng. Project name)", None
    NEXT_GENERATION_POOL_CONTROLLER_TEMP_ENG_PROJECT_NAME = 0x06, 0x03, 0x00000A, "Next Generation pool controller (Temp. Eng. Project name)", None

    # Sensors and Actuators Sensors, Contact Closures
    IOLINC = 0x07, 0x00, 0x00001A, "IOLinc", "2450"
    COMPACTA_EZSNS1W_SENSOR_INTERFACE_MODULE = 0x07, 0x01, 0x000004, "Compacta EZSns1W Sensor Interface Module", None
    COMPACTA_EZIO8T_IO_MODULE = 0x07, 0x02, 0x000012, "Compacta EZIO8T I/O Module", None
    COMPACTA_EZIO2X4_5010D_INSTEON_X10_INPUTOUTPUT_MODULE = 0x07, 0x03, 0x000005, "Compacta EZIO2X4 #5010D INSTEON / X10 Input/Output Module", None
    COMPACTA_EZIO8SA_IO_MODULE = 0x07, 0x04, 0x000013, "Compacta EZIO8SA I/O Module", None
    COMPACTA_EZSNSRF_5010E_RF_RECEIVER_INTERFACE_MODULE_FOR_DAKOTA_ALERTS_PRODUCTS = 0x07, 0x05, 0x000014, "Compacta EZSnsRF #5010E RF Receiver Interface Module for Dakota Alerts Products", None
    COMPACTA_EZISNSRF_SENSOR_INTERFACE_MODULE = 0x07, 0x06, 0x000015, "Compacta EZISnsRf Sensor Interface Module", None
    EZIO6I_6_INPUTS = 0x07, 0x07, 0x000039, "EZIO6I (6 inputs)", None
    EZIO4O_4_RELAY_OUTPUTS = 0x07, 0x08, 0x00003A, "EZIO4O (4 relay outputs)", None

    # Energy Management
    COMPACTA_EZENERGY = 0x09, 0x00, 0x000006, "Compacta EZEnergy", None
    ONSITEPRO_LEAK_DETECTOR = 0x09, 0x01, 0x000020, "OnSitePro Leak Detector", None
    ONSITEPRO_CONTROL_VALVE = 0x09, 0x02, 0x000021, "OnSitePro Control Valve", None
    ENERGY_INC_TED_5000_SINGLE_PHASE_MEASURING_TRANSMITTING_UNIT_MTU = 0x09, 0x03, 0x000025, "Energy Inc. TED 5000 Single Phase Measuring Transmitting Unit (MTU)", None
    ENERGY_INC_TED_5000_GATEWAY_USB = 0x09, 0x04, 0x000026, "Energy Inc. TED 5000 Gateway - USB", None
    ENERGY_INC_TED_5000_GATEWAY_ETHERNET = 0x09, 0x05, 0x00002A, "Energy Inc. TED 5000 Gateway - Ethernet", None
    ENERGY_INC_TED_3000_THREE_PHASE_MEASURING_TRANSMITTING_UNIT_MTU = 0x09, 0x06, 0x00002B, "Energy Inc. TED 3000 Three Phase Measuring Transmitting Unit (MTU)", None

    # Window Coverings
    SOMFY_DRAPE_CONTROLLER_RF_BRIDGE = 0x0E, 0x00, 0x00000B, "Somfy Drape Controller RF Bridge", None

    # Access Control
    WEILAND_DOORS_CENTRAL_DRIVE_AND_CONTROLLER = 0x0F, 0x00, 0x00000E, "Weiland Doors’ Central Drive and Controller", None
    WEILAND_DOORS_SECONDARY_CENTRAL_DRIVE = 0x0F, 0x01, 0x00000F, "Weiland Doors’ Secondary Central Drive", None
    WEILAND_DOORS_ASSIST_DRIVE = 0x0F, 0x02, 0x000010, "Weiland Doors’ Assist Drive", None
    WEILAND_DOORS_ELEVATION_DRIVE = 0x0F, 0x03, 0x000011, "Weiland Doors’ Elevation Drive", None

    # Security, Health, Safety
    FIRST_ALERT_ONELINK_RF_TO_INSTEON_BRIDGE = 0x10, 0x00, 0x000027, "First Alert ONELink RF to Insteon Bridge", None
    MOTION_SENSOR = 0x10, 0x01, 0x00004A, "Motion Sensor", "2420M"
    TRIGGERLINC_INSTEON_OPEN_CLOSE_SENSOR = 0x10, 0x02, 0x000049, "TriggerLinc - INSTEON Open / Close Sensor", "2421"

    def __init__(self, dev_cat, sub_cat, ipk=None, description=None, model=None):
        super().__init__()

        self._value_ = (dev_cat, sub_cat)
        self.category = Category(dev_cat)
        self.ipk = ipk
        self.description = description
        self.model = model

    @classmethod
    def _missing_(cls, value):
        for item in cls:
            if item.value[0] == value:
                return item
        obj = object.__new__(cls)
        obj._value_ = value
        obj.category = Category(value[0])
        obj.ipk = None
        obj.description = "Unknown"
        obj.model = None
        return obj

    def __str__(self):
        if self.model:
            return "%s model: %s" % (self.description, self.model)
        else:
            return "%s" % (self.description)
            