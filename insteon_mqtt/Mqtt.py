#===========================================================================
#
# Network and serial link management
#
#===========================================================================
import json
import logging
from . import Signal
from . import device as Dev

LOG = logging.getLogger(__name__)


class Mqtt:
    def __init__(self, mqtt_link, modem):
        self.signal_reload = Signal.Signal()

        self.modem = modem
        self.modem.signal_new_device.connect(self._new_device)

        self.link = mqtt_link
        self.link.signal_connected.connect(self._connected)
        self.link.signal_message.connect(self._message)

        self._cmd_topic = None
        self._set_topic = None
        self._state_topic = None
        self._qos = 1
        self._retain = True

        self.cmds = {
            'reload' : self._cmd_reload,
            'dbinit' : self._cmd_dbinit,
            'repair' : self._cmd_repair,
            }

    #-----------------------------------------------------------------------
    def load_config(self, config):
        self.link.load_config(config)

        if self._cmd_topic and self.link.connected:
            self._unsubscribe()

        self._cmd_topic = self._clean_topic(config['cmd_topic'])
        self._set_topic = self._clean_topic(config['set_topic'])
        self._state_topic = self._clean_topic(config['state_topic'])
        self._qos = config.get('qos', 1)
        self._retain = config.get('retain', True)

        if self.link.connected:
            self._subscribe()

    #-----------------------------------------------------------------------
    def publish(self, topic, payload, qos=None, retain=None):
        qos = self._qos if qos is None else qos
        retain = self._retain if retain is None else retain
        self.link.publish(topic, payload, qos, retain)

    #-----------------------------------------------------------------------
    def close(self):
        self.link.close()

    #-----------------------------------------------------------------------
    def _connected(self, link, connected):
        if connected:
            self._subscribe()

    #-----------------------------------------------------------------------
    def _new_device(self, modem, device):
        # TODO: what's the best way to handle this?  Don't want MQTT
        # specific stuff in the insteon devices but it would be nice
        # not to code up special cases for each here either.

        # Connect a callback for devices that report brightness.
        if hasattr(device, "signal_level_changed"):
            LOG.info("MQTT adding level changed device %s '%s'", device.addr,
                     device.name)

            device.signal_level_changed.connect(self._level_changed)

        elif isinstance(device, Dev.SmokeBridge):
            device.signal_state_change.connect(self._smoke_bridge)

        elif hasattr(device, "signal_active"):
            device.signal_active.connect(self._active)

    #-----------------------------------------------------------------------
    def _level_changed(self, device, level):
        LOG.info("MQTT received level change %s '%s' = %#04x",
                 device.addr, device.name, level)

        topic = "%s/%s" % (self._state_topic, device.addr.hex)
        payload = json.dumps({'level' : level})
        self.publish(topic, payload, retain=self._retain)

    #-----------------------------------------------------------------------
    def _active(self, device, is_active):
        LOG.info("MQTT received active change %s '%s' = %s",
                 device.addr, device.name, is_active)

        topic = "%s/%s" % (self._state_topic, device.addr.hex)
        payload = 'ON' if is_active else 'OFF'
        self.publish(topic, payload, retain=self._retain)

    #-----------------------------------------------------------------------
    def _smoke_bridge(self, device, condition):
        LOG.info("MQTT received smoke bridge alert %s '%s' = %s",
                 device.addr, device.name, condition)

        topic = "%s/%s" % (self._state_topic, device.addr.hex)
        payload = json.dumps({'condition' : condition})
        self.publish(topic, payload, retain=self._retain)

    #-----------------------------------------------------------------------
    def _message(self, link, msg):
        if msg.topic.startswith(self._cmd_topic):
            LOG.info("Command read: %s %s", msg.topic, msg.payload)
            self._handle_cmd(msg.topic, msg.payload)

        elif msg.topic.startswith(self._set_topic):
            LOG.info("Insteon command: %s %s", msg.topic, msg.payload)
            self._handle_set(msg.topic, msg.payload)

    #-----------------------------------------------------------------------
    def _handle_cmd(self, topic, payload):
        try:
            elem = payload.split(" ")
            cmd = elem[0]
            data = "".join(elem[1:]).strip()

            func = self.cmds.get(cmd, None)
            if func:
                func(data)
            else:
                LOG.error("Unknown MQTT command: %s %s", topic, payload)
        except:
            LOG.exception("Error running command: %s %s", topic, payload)

    #-----------------------------------------------------------------------
    def _handle_set(self, topic, payload):
        try:
            address = topic.split("/")[-1]
            device = self.modem.find(address)
            if not device:
                LOG.error("Unknown device requested: %s", address)
                return

            s = payload.lower()
            if s == b"on":
                device.run_command(level=0xff)
            elif s == b"off":
                device.run_command(level=0)
            else:
                data = json.loads(payload)
                device.run_command(**data)
        except:
            LOG.exception("Error running set command %s %s", topic, payload)

    #-----------------------------------------------------------------------
    def _subscribe(self):
        if self._cmd_topic:
            self.link.subscribe(self._cmd_topic+"/#", qos=self._qos)

        if self._set_topic:
            self.link.subscribe(self._set_topic+"/#", qos=self._qos)

    #-----------------------------------------------------------------------
    def _unsubscribe(self,):
        if self._cmd_topic:
            self.link.unsubscribe(self._cmd_topic+"/#")

        if self._set_topic:
            self.link.unsubscribe(self._set_topic+"/#")

    #-----------------------------------------------------------------------
    def _clean_topic(self, topic):
        if topic.endswith("/"):
            return topic[:-1]

        return topic

    #-----------------------------------------------------------------------
    def _cmd_reload(self, data):
        self.signal_reload.emit()

    #-----------------------------------------------------------------------
    def _cmd_dbinit(self, data):
        self.modem.reload_all()

    #-----------------------------------------------------------------------
    def _cmd_repair(self, data):
        device = self.modem.find(data)
        if not device:
            LOG.error("repair command unknown device %s", data)
            return

        try:
            device.repair()
        except:
            LOG.exception("Error trying to repair device %s", device.addr)

    #-----------------------------------------------------------------------
