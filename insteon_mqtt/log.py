#===========================================================================
#
# Logging utilities
#
#===========================================================================
import logging

# TODO: doc this stuff
UI = 21
logging.addLevelName(UI, "UI")


#===========================================================================
def get_logger(name="insteon_mqtt"):
    """TODO: doc
    """
    save = logging.getLoggerClass()
    try:
        logging.setLoggerClass(Logger)
        return logging.getLogger(name)
    finally:
        logging.setLoggerClass(save)

#===========================================================================


class Logger(logging.getLoggerClass()):
    """TODO: doc
    """
    def __init__(self, name):
        """TODO: doc
        """
        super().__init__(name)
        self._recorder = None

    #-----------------------------------------------------------------------
    def ui(self, msg, *args, **kwargs):
        """TODO: doc
        """
        if self.isEnabledFor(UI):
            self._log(UI, msg, args, **kwargs)

    #-----------------------------------------------------------------------
    def begin_record(self, min_level=UI):
        self._recorder = RecordingHandler(min_level)
        self.addHandler(self._recorder)

    #-----------------------------------------------------------------------
    def end_record(self):
        if not self._recorder:
            return []

        self.removeHandler(self._recorder)

        records = self._recorder.records
        self._recorder = None

        return records


#===========================================================================
class RecordingHandler(logging.Handler):
    """TODO: doc
    """

    def __init__(self, level):
        super().__init__(level)
        self.records = []

    #-----------------------------------------------------------------------
    def emit(self, record):
        """TODO: doc
        """
        self.records.append(record)
