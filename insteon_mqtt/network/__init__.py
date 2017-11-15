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

import platform
if platform.system() != 'Windows':
   from . import poll
else:
   # TODO: implemeent select
   pass
   
