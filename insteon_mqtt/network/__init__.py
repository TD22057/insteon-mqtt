#===========================================================================
#
# Network and serial link management
#
#===========================================================================
# flake8: noqa

__doc__ = """Network manage package

This package handles network and serial connections.  It uses select/poll
systems to manage multiple connections and read data notifications are
handled via the Signal class (loose coupling).

The network manager supports delayed connections (so remote hosts don't have
to be available right away) and automatic reconnections if links get closed
for maximum robustness.
"""

#===========================================================================

from .Link import Link
from .Serial import Serial
from .Mqtt import Mqtt

# Use Poll on non-windows systems - For windows we have to use select.
import platform  # pylint: disable=wrong-import-order
if platform.system() != 'Windows':
    from .poll import Manager
else:
    from .select import Manager
