#===========================================================================
#
# Message reading handlers.
#
#===========================================================================
# flake8: noqa

__doc__ = """Message handler classes.

Message handlers are classes that respond to messages read from the
PLM modem.  Handlers are responsible for figuring out what to do with
the read message and telling the Protocol class if that's the last
expected message in a squence or not.

Inbound messages can be:

1) Replies from commands we send to the modem.  For a std msg (8
   bytes), we'll get a echo reply w/ ACK/NAK (9 bytes).  If this
   fails, we'll get a 2 byte NAK.  After the ACK, we'll probably also
   get further messages in.  If we don't wait for these and continue
   writing messages, the modem won't send them (but will ACK them).
   So once we send a message, we need to know what the expected reply
   is going to be and wait for that.

2) inbound msg from modem when a device triggers and sends a message
   to the modem.  This will be an 11 byte std msg.

3) Device database reading.  Reading remote db's involves sending one
   command, getting an ACK, then reading a series of messages (1 per
   db entry) until we get a final message which ends the sequence.
"""


#===========================================================================
from .Base import Base
from .Broadcast import Broadcast
from .DeviceDbModify import DeviceDbModify
from .DeviceDbGet import DeviceDbGet
from .DeviceRefresh import DeviceRefresh
from .ModemDbGet import ModemDbGet
from .ModemDbModify import ModemDbModify
from .ModemLinkComplete import ModemLinkComplete
from .ModemLinkStart import ModemLinkStart
from .ModemReset import ModemReset
from .ModemScene import ModemScene
from .StandardCmd import StandardCmd
from .ExtendedCmdResponse import ExtendedCmdResponse
from .ThermostatCmd import ThermostatCmd
