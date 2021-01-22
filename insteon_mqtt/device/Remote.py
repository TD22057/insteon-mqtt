#===========================================================================
#
# Remote module
#
#===========================================================================
import time
from .BatterySensor import BatterySensor
from .functions import ManualCtrl
from .. import log
from .. import on_off
from .. import message as Msg
from .. import handler
from ..Signal import Signal
from .. import util

LOG = log.get_logger()


class Remote(ManualCtrl, BatterySensor):
    """Insteon multi-button battery powered mini-remote device.

    This class can be used for 1, 4, 6 or 8 (really any number) of battery
    powered button remote controls.

    The issue with a battery powered remotes is that we can't download the
    link database without the remote being on.  You can trigger the remote
    manually and then quickly send an MQTT command with the payload 'getdb'
    to download the database.  We also can't test to see if the local
    database is current or what the current motion state is - we can really
    only respond to the remote when it sends out a message.

    State changes are communicated by emitting signals.  Other classes can
    connect to these signals to perform an action when a change is made to
    the device (like sending MQTT messages).  Supported signals are:
    """
    # This defines what is the minimum time between battery status requests
    # for devices that support it.  Value is in seconds
    # Currently set at 4 Days
    BATTERY_TIME = (60 * 60) * 24 * 4

    # Voltages below this value will report as low
    # Full charge value looks to be 3.7v which make sense for Li-Ion
    # It is hard to say what a good number is here.  Using recommendations from
    # https://learn.adafruit.com/li-ion-and-lipoly-batteries/voltages
    # I also tried to drain the battery of one of my devices
    BATTERY_VOLTAGE_LOW = 3.4

    def __init__(self, protocol, modem, address, name, num_button):
        """Constructor

        Args:
          protocol (Protocol):  The Protocol object used to communicate
                   with the Insteon network.  This is needed to allow the
                   device to send messages to the PLM modem.
          modem (Modem):  The Insteon modem used to find other devices.
          address (Address):  The address of the device.
          name (str):  Nice alias name to use for the device.
          num_button (int):  Number of buttons on the remote.
        """
        assert num_button > 0
        super().__init__(protocol, modem, address, name)

        self.num = num_button
        self.type_name = "mini_remote_%d" % self.num

        # Even though all buttons use the same callback this creats
        # symmetry with the rest of the codebase
        self.group_map = {}
        for i in range(1, self.num + 1):
            self.group_map[i] = self.handle_on_off

        self.cmd_map.update({
            'get_battery_voltage' : self.get_extended_flags,
            })

        # This allows for a short timer between sending automatic battery
        # requests.  Otherwise, a request may get queued multiple times
        self._battery_request_time = 0

    #-----------------------------------------------------------------------
    @property
    def battery_voltage_time(self):
        """Returns the timestamp of the last battery voltage report from the
        saved metadata
        """
        meta = self.db.get_meta('Remote')
        ret = 0
        if isinstance(meta, dict) and 'battery_voltage_time' in meta:
            ret = meta['battery_voltage_time']
        return ret

    #-----------------------------------------------------------------------
    @battery_voltage_time.setter
    def battery_voltage_time(self, val):
        """Saves the timestamp of the last battery voltage report to the
        database metadata
        Args:
          val:    (timestamp) time.time() value
        """
        meta = {'battery_voltage_time': val}
        existing = self.db.get_meta('Remote')
        if isinstance(existing, dict):
            existing.update(meta)
            self.db.set_meta('Remote', existing)
        else:
            self.db.set_meta('Remote', meta)

    #-----------------------------------------------------------------------
    def handle_extended_flags(self, msg, on_done):
        """Receives the extended flags payload from the device

        Primarily this is used to get the battery voltage
        """
        # D10 voltage in tenth position, but remember starts at 0
        batt_volt = msg.data[9] / 50
        LOG.info("Remote %s battery voltage is %s", self.label,
                 batt_volt)
        self.battery_voltage_time = time.time()
        # Signal low battery
        self.signal_low_battery.emit(self,
                                     batt_volt <= self.BATTERY_VOLTAGE_LOW)
        on_done(True, "Battery voltage is %s" % batt_volt, msg.data[9])

    #-----------------------------------------------------------------------
    def link_data(self, is_controller, group, data=None):
        """Create default device 3 byte link data.

        This is the 3 byte field (D1, D2, D3) stored in the device database
        entry.  This overrides the defaults specified in base.py for
        specific values used by multi-group devices.

        For controllers, the default fields are:
           D1: number of retries (0x03)
           D2: unknown (0x00)
           D3: the group number on the local device (0x01)

        For responders, the default fields are:
           D1: on level for switches and dimmers (0xff)
           D2: 0x00
           D3: the group number on the local device (0x01)

        Args:
          is_controller (bool): True if the device is the controller, false
                        if it's the responder.
          group (int): The group number of the controller button or the
                group number of the responding button.
          data (bytes[3]): Optional 3 byte data entry.  If this is None,
               defaults are returned.  Otherwise it must be a 3 element list.
               Any element that is not None is replaced with the default.

        Returns:
          bytes[3]: Returns a list of 3 bytes to use as D1,D2,D3.
        """
        if is_controller:
            defaults = [0x03, 0x00, 0x00]

        # Responder data is always link dependent.  Since nothing was given,
        # assume the user wants to turn the device on (0xff).
        else:
            defaults = [0xff, 0x00, 0x01]

        # For each field, use the input if not -1, else the default.
        return util.resolve_data3(defaults, data)

    #-----------------------------------------------------------------------
    def get_extended_flags(self, on_done):
        """Requests the Extended Flags from the Device

        Notably, these flags contain the battery voltage.
        """
        data = bytes([0x01] + [0x00] * 13)
        msg = Msg.OutExtended.direct(self.addr, 0x2e, 0x00, data)
        msg_handler = handler.ExtendedCmdResponse(msg,
                                                  self.handle_extended_flags,
                                                  on_done=on_done)
        self.send(msg, msg_handler)

    #-----------------------------------------------------------------------
    def auto_check_battery(self):
        """Queues a Battery Voltage Request if Necessary

        If the device supports it, and the requisite amount of time has
        elapsed, queue a battery request.
        """
        if (self.db.desc is not None and
                self.db.desc.model.split("-")[0] == "2342"):
            # This is a device that supports battery requests
            last_checked = self.battery_voltage_time
            # Don't send this message more than once every 5 minutes no
            # matter what
            if (last_checked + self.BATTERY_TIME <= time.time() and
                    self._battery_request_time + 300 <= time.time()):
                self._battery_request_time = time.time()
                LOG.info("Remote %s: Auto requesting battery voltage",
                         self.label)
                self.get_extended_flags(None)

    #-----------------------------------------------------------------------
    def awake(self, on_done):
        """Injects a Battery Voltage Request if Necessary

        Queue a battery request that should go out now, since the device is
        awake.
        """
        self.auto_check_battery()
        super().awake(on_done)

    #-----------------------------------------------------------------------
    def _pop_send_queue(self):
        """Injects a Battery Voltage Request if Necessary

        Queue a battery request that should go out now, since the device is
        awake.
        """
        self.auto_check_battery()
        super()._pop_send_queue()

    #-----------------------------------------------------------------------
