#===========================================================================
#
# Insteon messages
#
#===========================================================================

from .DbFlags import DbFlags
from .Flags import Flags

# Messages from PLM modem to the host (codes >= 0x60)
from .InpAllLinkComplete import InpAllLinkComplete
from .InpAllLinkFailure import InpAllLinkFailure
from .InpAllLinkRec import InpAllLinkRec
from .InpAllLinkStatus import InpAllLinkStatus
#from .InpExtended import InpExtended
from .InpStandard import InpStandard, InpExtended
from .InpUserReset import InpUserReset
from .InpUserSetBtn import InpUserSetBtn

# Messages from the host to the PLM modem (codes < 0x06)
# These can be sent to the modem as commands.
from .OutAllLink import OutAllLink
from .OutAllLinkCancel import OutAllLinkCancel
from .OutAllLinkStart import OutAllLinkStart
from .OutAllLinkGetFirst import OutAllLinkGetFirst
from .OutAllLinkGetNext import OutAllLinkGetNext
from .OutAllLinkUpdate import OutAllLinkUpdate
from .OutResetPlm import OutResetPlm
from .OutStandard import OutStandard, OutExtended

# Message handler status fields.
UNKNOWN = -1
CONTINUE = 1
FINISHED = 2

# Mapping of message type codes to message class.
types = {
    # PLM -> host messages
    0x50 : InpStandard,
    0x51 : InpExtended,
    0x53 : InpAllLinkComplete,
    0x54 : InpUserSetBtn,
    0x55 : InpUserReset,
    0x56 : InpAllLinkFailure,
    0x57 : InpAllLinkRec,
    0x58 : InpAllLinkStatus,

    # host -> PLM messages
    0x61 : OutAllLink,
    0x62 : OutStandard,  # Handles reading standard and extended
    0x64 : OutAllLinkStart,
    0x64 : OutAllLinkCancel,
    0x67 : OutResetPlm,
    0x69 : OutAllLinkGetFirst,
    0x6a : OutAllLinkGetNext,
    0x6f : OutAllLinkUpdate,
    }

# TODO: log add responder, controller to modem
# TODO: log add responder, controller to device
