#===========================================================================
#
# Dimmer module
#
#===========================================================================
from .Device import Device
from . import msg as Msg
from .Address import Address
from .. import Signal
import logging

s_log = logging.getLogger(__name__)

class DeviceDbHandler:
    def __init__(self, device):
        self.device = device
        self.have_ack = False

    def msg_received(self, handler, msg):
        # Probably an echo back of our sent message.
        if isinstance(msg, Msg.OutExtended):
            if msg.to_addr == self.device.addr and msg.cmd1 == 0x2f:
                if not msg.is_ack:
                    s_log.error("%s NAK response", self.device.addr)
                    
                return Msg.CONTINUE

            return Msg.UNKNOWN

        # ACK 
        elif isinstance(msg, Msg.OutStandard):
            # See if this is the first response record.  It doens't
            # have any data - it's just a direct ack.
            if msg.to_addr != self.device.addr or msg.cmd1 != 0x2f:
                return Msg.UNKNOWN

            self.have_ack = True
            s_log.info("received direct ack %s", self.device.addr)
            return Msg.CONTINUE

        elif isinstance(msg, Msg.InpExtended):
            if msg.from_addr != self.device.addr or msg.cmd1 != 0x2f:
                return Msg.UNKNOWN

            sum = 0
            for i in msg.data[4:13]:
                sum += i
            if i == 0x00:
                return Msg.FINISHED

            self.device.add_db_rec(msg)
            return Msg.CONTINUE

        return Msg.UNKNOWN

        

class StandardCmdHandler:
    def __init__(self, device, cmd1):
        self.device = device
        self.cmd1 = cmd1

    def msg_received(self, handler, msg):
        # Probably an echo back of our sent message.
        if isinstance(msg, Msg.OutStandard):
            if msg.to_addr == self.device.addr and msg.cmd1 == self.cmd1:
                if not msg.is_ack:
                    s_log.error("%s NAK response", self.device.addr)
                    
                return Msg.CONTINUE

            return Msg.UNKNOWN

        # See if this is the standard message ack/nak we're expecting.
        if isinstance(msg, Msg.InpStandard):
            if (msg.from_addr == self.device.addr and msg.cmd1 == self.cmd1):
                if msg.flags.type == Msg.Flags.DIRECT_ACK:
                    self.device.handle_direct_ack(msg)
                elif msg.flags.type == Msg.Flags.DIRECT_NAK:
                    s_log.error("%s NAK response", self.device.addr)

                return Msg.FINISHED
                
        return Msg.UNKNOWN
        
class Dimmer (Device):
    def __init__(self, handler, address, name=None):
        super().__init__(handler, address, name)
        self._level = None
        self.db = []
        self.db_unused = []
        
        self.signal_level_changed = Signal.Signal() # (Dimmer, level)

    #-----------------------------------------------------------------------
    def pair(self, modem):
        s_log.info( "Dimmer %s pairing with modem", self.addr)
        # TODO: pair with modem
        pass

    #-----------------------------------------------------------------------
    def add_db_rec(self, msg):
        assert(isinstance(msg, Msg.InpExtended))

        assert(msg.data[1] == 0x01)  # record response
        msg.mem_high = msg.data[2]
        msg.mem_low = msg.data[3]
        msg.group = msg.data[6]
        msg.link_addr = Address.read(msg.data, 7)
        msg.on_level = msg.data[10]
        msg.ramp_rate = msg.data[11]
        msg.link_data = msg.data[10:13]

        # D6 = rec_flags
        msg.ctrl = Msg.DbFlags.read(msg.data, 5)
        if not msg.ctrl.in_use:
            s_log.info("Ignoring modem db record in_use = False")
            self.db_unused.append(msg)
            return
        
        s_log.info("Adding db record for %s grp: %s lev: %s",
                      msg.link_addr, msg.group, msg.on_level)
        # TODO: save in db
        self.db.append(msg)
        
    #-----------------------------------------------------------------------
    def is_on(self):
        return not self._level

    #-----------------------------------------------------------------------
    def level(self):
        return self._level

    #-----------------------------------------------------------------------
    def handle_broadcast(self, msg):
        # ACK of the broadcast - ignore this.
        if msg.cmd1 == 0x06:
            s_log.info( "Dimmer %s broadcast ACK grp: %s", self.addr, msg.group)
            return

        # On command.  How do we tell the level?  It's not in the
        # message anywhere.
        elif msg.cmd1 == 0x11:
            s_log.info( "Dimmer %s broadcast ON grp: %s", self.addr, msg.group)
            self._level = 0xff
            self.signal_level_changed.emit(self, self._level)
            
        # Off command.
        elif msg.cmd1 == 0x13:
            s_log.info( "Dimmer %s broadcast OFF grp: %s", self.addr, msg.group)
            self._level = 0x00
            self.signal_level_changed.emit(self, self._level)
        
        # Find the group in the device database
        #group = self.db.find_group(msg.group)

        # Signal each member of the group with the command
        #for device in group:
        #    device.handle_group_cmd(self.addr, msg)   
        
    #-----------------------------------------------------------------------
    def handle_direct_ack(self, msg):
        self._level = msg.cmd2
        self.signal_level_changed.emit(self, self._level)
        
    #-----------------------------------------------------------------------
    def on(self, level=0xFF, instant=False):
        s_log.info( "Dimmer %s cmd: on %s", self.addr, level)
        assert(level >= 0 and level <= 0xff)
        
        cmd1 = 0x11 if not instant else 0x21
        msg = Msg.OutStandard.direct(self.addr, cmd1, level)
        self.handler.send(msg, StandardCmdHandler(self, cmd1))

    #-----------------------------------------------------------------------
    def off(self, instant=False):
        s_log.info( "Dimmer %s cmd: off", self.addr)

        cmd1 = 0x13 if not instant else 0x21
        msg = Msg.OutStandard.direct(self.addr, cmd1, 0x00)
        self.handler.send(msg, StandardCmdHandler(self, cmd1))

    #-----------------------------------------------------------------------
    def incrementUp(self):
        s_log.info( "Dimmer %s cmd: increment up", self.addr)
        msg = Msg.OutStandard.direct(self.addr, 0x15, 0x00)
        self.handler.send(msg, StandardCmdHandler(self, 0x15))

    #-----------------------------------------------------------------------
    def incrementDown(self):
        s_log.info( "Dimmer %s cmd: increment down", self.addr)
        msg = Msg.OutStandard.direct(self.addr, 0x16, 0x00)
        self.handler.send(msg, StandardCmdHandler(self, 0x16))

    #-----------------------------------------------------------------------
    def manualStartUp(self):
        s_log.info( "Dimmer %s cmd: manual start up", self.addr)
        msg = Msg.OutStandard.direct(self.addr, 0x17, 0x01)
        self.handler.send(msg, StandardCmdHandler(self, 0x17))

    #-----------------------------------------------------------------------
    def manualStartDown(self):
        s_log.info( "Dimmer %s cmd: manual start down", self.addr)
        msg = Msg.OutStandard.direct(self.addr, 0x17, 0x00)
        self.handler.send(msg, StandardCmdHandler(self, 0x17))

    #-----------------------------------------------------------------------
    def manualStop(self):
        s_log.info( "Dimmer %s cmd: manual stop", self.addr)
        msg = Msg.OutStandard.direct(self.addr, 0x18, 0x00)
        self.handler.send(msg, StandardCmdHandler(self, 0x18))

    #-----------------------------------------------------------------------
    def set(self, active, level=0xFF, instant=False):
        if active:
            self.on(level, instant)
        else:
            self.off(instant)

    #-----------------------------------------------------------------------
    def run_command(self, **kwargs):
        s_log.info("Dimmer command: %s", kwargs)
        if 'level' in kwargs:
            level = int(kwargs.pop('level'))
            instant = bool(kwargs.pop('instant', False))
            if level == 0:
                self.off(instant)
            else:
                self.on(level, instant)

        elif 'increment' in kwargs:
            dir = kwargs.pop('increment')
            if dir == +1:
                self.incrementUp()
            elif dir == -1:
                self.incrementDown()
            else:
                s_log.error("Invalid increment %s", dir)

        elif 'getdb' in kwargs:
            self.get_db()
            
        else:
            s_log.error("Invalid commands to dimmer")
        
    #-----------------------------------------------------------------------
    def _update(self):
        # TODO: send status command, update internal state
        pass

    #-----------------------------------------------------------------------
    def get_db(self):
        s_log.info("Device sending get first db record command")
        
        # Request that the device send us all it's database records.
        msg = Msg.OutExtended.direct(self.addr, 0x2f, 0x00, bytes(14))
        msg_handler = DeviceDbHandler(self)
        self.handler.send(msg, msg_handler)
        
    #-----------------------------------------------------------------------
