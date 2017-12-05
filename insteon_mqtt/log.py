#===========================================================================
#
# Logging utilities
#
#===========================================================================
import logging
import logging.handlers

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
def initialize(level=logging.INFO, screen=True, file=None):
    """TODO: doc
    """
    print("LOG:",level,screen,file)
    log_obj = get_logger()
    log_obj.setLevel(level)

    # Initialize basic logging.
    fmt = '%(asctime)s %(levelname)s %(module)s: %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(fmt, datefmt)

    if screen:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        log_obj.addHandler(handler)

    if file:
        handler = logging.handlers.WatchedFileHandler(file)
        handler.setFormatter(formatter)
        log_obj.addHandler(handler)

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
