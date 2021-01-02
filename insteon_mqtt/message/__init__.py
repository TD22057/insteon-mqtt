#===========================================================================
#
# Insteon messages
#
#===========================================================================
# flake8: noqa

__doc__ = """Insteon message classes.

Each message has it's own class which can convert between the byte
stream and the message.  All messages start with the byte 0x02
followed by the message ID byte.  Mapping from the ID by to the class
type is handled by the messages.types dictionary.

Class names that start with 'Inp' are input messages that are sent
from the PLM modem to the host computer.  These are either replies to
commands or broadcast commands triggered by Insteon devices
(e.g. motion, pushing a light switch, etc).

Class names that start with 'Out' are output messages that are sent
from the host computer to the PLM modem as commands.  These can also
be inputs because the PLM modem will repeat messages back as ACK/NAK
results.
"""

from .Base import Base
from .Timed import Timed

# Bit level message flags
from .DbFlags import DbFlags
from .Flags import Flags

# Message Types
from .CmdType import CmdType

# Messages from PLM modem to the host (codes >= 0x60)
from .InpAllLinkComplete import InpAllLinkComplete
from .InpAllLinkFailure import InpAllLinkFailure
from .InpAllLinkRec import InpAllLinkRec
from .InpAllLinkStatus import InpAllLinkStatus
from .InpStandard import InpStandard, InpExtended
from .InpUserReset import InpUserReset
from .InpUserSetBtn import InpUserSetBtn
from .Unreachable import Unreachable

# Messages from the host to the PLM modem (codes < 0x06)
from .OutAllLinkCancel import OutAllLinkCancel
from .OutAllLinkGetFirst import OutAllLinkGetFirst
from .OutAllLinkGetNext import OutAllLinkGetNext
from .OutAllLinkUpdate import OutAllLinkUpdate
from .OutModemLinking import OutModemLinking
from .OutModemScene import OutModemScene
from .OutResetModem import OutResetModem
from .OutStandard import OutStandard, OutExtended

# Hub Messages
from .HubUnknown import HubRFUnknown

# Message handler status fields.
UNKNOWN = -1
CONTINUE = 1
FINISHED = 2

# Mapping of message type codes to message class.
types = {
    # modem -> host messages
    0x50 : InpStandard,
    0x51 : InpExtended,
    0x53 : InpAllLinkComplete,
    0x54 : InpUserSetBtn,
    0x55 : InpUserReset,
    0x56 : InpAllLinkFailure,
    0x57 : InpAllLinkRec,
    0x58 : InpAllLinkStatus,
    0x5c : Unreachable,

    # host -> modem messages
    0x61 : OutModemScene,
    0x62 : OutStandard,  # Handles reading standard and extended
    0x64 : OutModemLinking,
    0x65 : OutAllLinkCancel,
    0x67 : OutResetModem,
    0x69 : OutAllLinkGetFirst,
    0x6a : OutAllLinkGetNext,
    0x6f : OutAllLinkUpdate,

    # Hub Messages
    0x7f : HubRFUnknown,
    }
