#===========================================================================
#
# Insteon device Base classes
#
#===========================================================================
# flake8: noqa

__doc__ = """Insteon device Base classes.

These are all abstract classes that provide the base support for device
classes to further extend.  ONLY ONE BASE CLASS SHOULD BE INHERITTED by
a device class.

Base - Provides very basic support for devices that emit controller signals
but do not have any responder objects.  This include things like BatterSensors
and SmokeBridge.

ResponderBase - Extendes Base to provide basic functionality for devices that
have simple responder objects.  This includes things like Switches and
Outlets.

DimmerBase - Extends ResponderBase and ManualCtrl to provide dimmer
functionality for devices that have responders that can be dimmed, such as
Dimmers, FanLinc, KeypadLincDimmer.
"""

#===========================================================================

from .Base import Base
from .ResponderBase import ResponderBase
from .DimmerBase import DimmerBase
