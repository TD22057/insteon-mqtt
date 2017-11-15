#===========================================================================
#
# Network and serial link management
#
#===========================================================================

__doc__ = """TODO: doc"""

#===========================================================================

from .Link import Link
from .Serial import Serial
from .Mqtt import Mqtt

# Use Poll on non-windows systems - For windows we have to use select.
import platform
if platform.system() != 'Windows':
   from .poll import Manager
else:
   # TODO: implemeent select
   #from .select import Manager
   pass

