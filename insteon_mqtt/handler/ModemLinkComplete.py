#===========================================================================
#
# Modem all link complete handler.
#
#===========================================================================

from .. import log
from .. import message as Msg
from .. import util
from .Base import Base

LOG = log.get_logger()


class ModemLinkComplete(Base):
    """Modem linking mode completed handler.

    This is called after the modem was placed in linking mode and a
    connection with a device was made.  The modem sends us the connection
    link data so we can update the modem's database.
    """
    def __init__(self, modem):
        """Constructor

        Args
          modem (Modem):  The PLM modem to update.
        """
        super().__init__()
        self.modem = modem

    #-----------------------------------------------------------------------
    def msg_received(self, protocol, msg):
        """See if we can handle the message.

        Args:
          protocol (Protocol):  The Insteon Protocol object
          msg:  Insteon message object that was read.

        Returns:
          Msg.UNKNOWN if we can't handle this message.
          Msg.CONTINUE if we handled the message and expect more.
          Msg.FINISHED if we handled the message and are done.
        """
        # Import here - at file scope this makes a circular import which is
        # ok in Python>=3.5 but not 3.4.
        from .. import db

        # All linking was successful.
        if isinstance(msg, Msg.InpAllLinkComplete):
            # FUTURE: use msg.dev_cat and msg.dev_subcat for
            # device discovery.
            #   - build device class
            #   - add device to modem (and save it in config? or db?)
            #   - download device db
            #   - link db to modem
            #   - call pair() command to finish

            if msg.cmd == Msg.InpAllLinkComplete.Cmd.DELETE:
                # Can this ever occur?  We can't tell controller vs responder
                # from this message so we don't know what was actually
                # deleted.
                LOG.ui("Modem db entry deleted via linking")
                self.modem.refresh()

            # Set button was used to add a new controller or responder
            # link to the modem.
            else:
                # Create a new entry and add it to the modem's database.
                is_ctrl = msg.cmd == Msg.InpAllLinkComplete.Cmd.CONTROLLER
                LOG.ui("Modem db entry added via linking: %s grp %s %s",
                       msg.addr, msg.group, util.ctrl_str(is_ctrl))

                # Modem does this for manual links when it's the controller -
                # so recreate it here.  I don't think these data entries are
                # used for anything.
                if is_ctrl:
                    data = [msg.dev_cat, msg.dev_subcat, msg.firmware]
                else:
                    data = self.modem.link_data(msg.group, is_ctrl)

                entry = db.ModemEntry(msg.addr, msg.group, is_ctrl, data)
                self.modem.db.add_entry(entry)

            return Msg.FINISHED

        return Msg.UNKNOWN

    #-----------------------------------------------------------------------
