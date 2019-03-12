#===========================================================================
#
# MQTT reply to commands class
#
#===========================================================================
import json
import enum


class Reply:
    """MQTT session replay.

    This class stores a reply made from the server to a remote command line
    process and is used to send information about the server status to the
    command line tool so it can report nicer messages and know when the
    operation completes.
    """
    class Type(enum.Enum):
        END = "END"  # Command has finished.
        MESSAGE = "MESSAGE"  # General status message
        ERROR = "ERROR"  # Error message

    #-----------------------------------------------------------------------
    @staticmethod
    def from_json(msg):
        """Convert from JSON data.

        Args:
          msg (str):  The json string to read from.

        Returns:
          Reply:  Returns a created Reply object.
        """
        data = json.loads(msg)
        return Reply(Reply.Type(data["type"]), data["data"])

    #-----------------------------------------------------------------------
    def __init__(self, type, data=None):
        """Constructor

        Args:
          type (Type):  The type of reply to send.
          data:  Addition data (usually a string) to send.
        """
        assert isinstance(type, Reply.Type)

        self.type = type
        self.data = data

    #-----------------------------------------------------------------------
    def to_json(self):
        """Convert the message to JSON format.

        Returns:
          str:  Returns the JSON data converted to a string.
        """
        data = {"type" : self.type.value, "data" : self.data}
        return json.dumps(data)

    #-----------------------------------------------------------------------

#===========================================================================
