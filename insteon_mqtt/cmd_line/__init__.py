#===========================================================================
#
# Insteon-MQTT command line module
#
#===========================================================================
# flake8: noqa

__doc__ = """Command line parsing and execution.

This package parses the command line arguments and can start the main server
or send a variety of commands to a running server process.
"""

#===========================================================================
from . import device
from . import modem
from . import util

from .main import main
