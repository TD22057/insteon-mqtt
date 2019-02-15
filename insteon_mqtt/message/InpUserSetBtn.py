#===========================================================================
#
# Input insteon user pressed set button message.
#
#===========================================================================
from .Base import Base


class InpUserSetBtn(Base):
    """User pressed the PLM set button.

    This is sent from the PLM modem to the host when the user presses the
    modem set button.
    """
    # pylint: disable=abstract-method

    msg_code = 0x54
    fixed_msg_size = 3

    events = {
        0x02 : 'SET_TAPPED',
        0x03 : 'SET_HOLD',
        0x04 : 'SET_RELEASED',
        0x12 : 'BTN2_TAPPED',
        0x13 : 'BTN2_HOLD',
        0x14 : 'BTN2_RELEASED',
        0x22 : 'BTN3_TAPPED',
        0x23 : 'BTN3_HOLD',
        0x24 : 'BTN3_RELEASED',
        }

    #-----------------------------------------------------------------------
    @classmethod
    def from_bytes(cls, raw):
        """Read the message from a byte stream.

        This should only be called if raw[1] == msg_code and len(raw) >=
        msg_size().

        Args:
          raw (bytes):  The current byte stream to read from.

        Returns:
          Returns the constructed InpUserSetBtn object.
        """
        assert len(raw) >= InpUserSetBtn.fixed_msg_size
        assert raw[0] == 0x02 and raw[1] == InpUserSetBtn.msg_code

        event = InpUserSetBtn.events.get(raw[2], 'UNKNOWN')
        return InpUserSetBtn(event)

    #-----------------------------------------------------------------------
    def __init__(self, event):
        """Constructor

        Args:
          event (int):  The event code.  See the class attributes for options.
        """
        super().__init__()

        assert event in InpUserSetBtn.events.values()
        self.event = event

    #-----------------------------------------------------------------------
    def __str__(self):
        return "Set btn: %s" % self.event

    #-----------------------------------------------------------------------

#===========================================================================
