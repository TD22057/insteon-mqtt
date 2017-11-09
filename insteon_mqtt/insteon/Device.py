#===========================================================================
#
# Base device class
#
#===========================================================================
from .Address import Address

class Device:
    def __init__(self, address, name=None):
        self.addr = Address(address)
        self.name = name
        self.db = {}

    #-----------------------------------------------------------------------
    def ping(self):
        # TODO: send ping command
        pass

    #-----------------------------------------------------------------------
    def load_db_file(self, db_path):
        # TODO: load device database
        pass

    #-----------------------------------------------------------------------
    def save_db_file(self, db_path):
        # TODO: save device database
        pass

    #-----------------------------------------------------------------------
