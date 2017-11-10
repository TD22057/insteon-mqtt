#===========================================================================
#
# Network and serial link management
#
#===========================================================================
import json
import logging
from . import Signal

class Mqtt:
    def __init__(self, link, modem):
        self.signal_reload = Signal.Signal()

        self.modem = modem
        self.modem.signal_new_device.connect(self._new_device)

        self.link = link
        self.link.signal_connected.connect(self._connected)
        self.link.signal_message.connect(self._message)

        self._cmd_topic = None
        self._set_topic = None
        self._state_topic = None

        self.log = logging.getLogger(__name__)

        self._cmds = {
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

        if self.link.connected:
            self._subscribe()

    #-----------------------------------------------------------------------
    def publish(self, topic, payload, qos=1, retain=False):
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
        if hasattr(device, "signal_level_changed"):
            self.log.info("MQTT adding level changed device %s '%s'",
                          device.addr, device.name)
            
            device.signal_level_changed.connect(self._level_changed)

    #-----------------------------------------------------------------------
    def _level_changed(self, device, level):
        self.log.info("MQTT received level change %s '%s' = %#04x",
                      device.addr, device.name, level)
        
        topic = "%s/%s" % (self._state_topic, device.addr.hex)
        payload = json.dumps( { 'level' : level } )
        self.publish(topic, payload, retain=False) # TODO: True
        
    #-----------------------------------------------------------------------
    def _message(self, link, msg):
        if msg.topic.startswith(self._cmd_topic):
            self.log.info("Command read: %s %s", msg.topic, msg.payload)
            self._handle_cmd(msg.topic, msg.payload)

        elif msg.topic.startswith(self._set_topic):
            self.log.info("Insteon command: %s %s", msg.topic, msg.payload)
            self._handle_set(msg.topic, msg.payload)

    #-----------------------------------------------------------------------
    def _handle_cmd(self, topic, payload):
         try:
             elem = msg.payload.split(" ")
             cmd = elem[0]
             data = "".join(elem[1:]).strip()

             func = getattr(self, "_cmd_{}".format(cmd), None)
             if func:
                 func(data)
             else:
                 self.log.error("Unknown MQTT command: %s %s", topic, payload)
         except:
             self.log.exception("Error running command: %s %s", topic, payload)

    #-----------------------------------------------------------------------
    def _handle_set(self, topic, payload):
         try:
             data = json.loads(payload)

             address = topic.split("/")[-1]
             device = self.modem.find(address)
             device.run_command(**data)
         except:
             self.log.exception("Error running set command %s %s", topic,
                                payload)

    #-----------------------------------------------------------------------
    def _subscribe(self):
        if self._cmd_topic:
            self.link.subscribe(self._cmd_topic+"/#", qos=1)
        if self._set_topic:
            self.link.subscribe(self._set_topic+"/#", qos=1)

    #-----------------------------------------------------------------------
    def _unsubscribe(self, topic):
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
        try:
            device = self.modem.find(data)
            device.repair()
        except:
            self.log.exception("Error trying to repair device %s", data)

    #-----------------------------------------------------------------------
