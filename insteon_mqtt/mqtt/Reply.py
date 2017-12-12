#===========================================================================
#
# MQTT reply to commands class
#
#===========================================================================
import json
import enum


class Reply:
    """TODO: doc
    """
    class Type(enum.Enum):
        END = "END"
        MESSAGE = "MESSAGE"
        ERROR = "ERROR"

    #-----------------------------------------------------------------------
    @staticmethod
    def from_json(data):
        return Reply(Reply.Type(data["type"]), data["data"])

    #-----------------------------------------------------------------------
    def __init__(self, type, data=None):
        assert isinstance(type, Reply.Type)

        self.type = type
        self.data = data

    #-----------------------------------------------------------------------
    def to_json(self):
        data = {"type" : self.type.value, "data" : self.data}
        return json.dumps(data)

    #-----------------------------------------------------------------------

#===========================================================================
