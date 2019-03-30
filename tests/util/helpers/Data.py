#===========================================================================
#
# Data class - used to easily return multiple values from fixtures and
# access them in the minimum amount of code.
#
#===========================================================================


class Data (dict):
    """dict like object with attribute (data.xx) access"""
    def __init__(self, **kwargs):
        self.update(kwargs)

    def getAll(self, attrs):
        return [getattr(self, i) for i in attrs]

    def __getattribute__(self, name):
        if name in self:
            return self[name]
        return dict.__getattribute__(self, name)
