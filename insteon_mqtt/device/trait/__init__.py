#===========================================================================
#
# Insteon device trait classes
#
#===========================================================================
# flake8: noqa

__doc__ = """Insteon device trait classes.

Certain device functions are common across multiple device types.

These trait classes provide a single location to define these functions so
that they can be reused across multiple device types.  Each trait class
should be a concise group of related functions.  The goal is to eliminate code
duplication.

Each trait class inherits the Base device class.  Certain class methods are
expected to be implemented by the child classes.
"""

#===========================================================================

from .Scene import Scene
