#===========================================================================
#
# Device database difference tracker
#
#===========================================================================


class DbDiff:
    """TODO: doc
    """

    def __init__(self, addr):
        """TODO: doc
        """
        self.addr = addr
        self.add_entries = []
        self.del_entries = []

    def __len__(self):
        """TODO: doc
        """
        return len(self.add_entries) + len(self.del_entries)

    def add(self, entry):
        """TODO: doc
        """
        self.add_entries.append(entry)

    def remove(self, entry):
        """TODO: doc
        """
        self.del_entries.append(entry)
