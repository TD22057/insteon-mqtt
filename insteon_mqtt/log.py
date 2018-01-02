#===========================================================================
#
# Logging utilities
#
#===========================================================================
import logging
import logging.handlers

# TODO: doc this stuff
UI_LEVEL = 21
logging.addLevelName(UI_LEVEL, "UI")


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
def initialize(level=None, screen=None, file=None, config=None):
    """TODO: doc
    """
    # Config variables are used if the config is input and if a direct
    # input variable is not set.
    if config:
        # Read the logging config and initialize the library logger.
        data = config.get("logging", {})

        if level is None:
            level = data.get("level", None)
        if screen is None:
            screen = data.get("screen", None)
        if file is None:
            file = data.get("file", None)

    # Apply defaults if none were set.
    level = level if level is not None else logging.INFO
    screen = bool(screen) if screen is not None else True
    file = file if file is not None else None

    # Set the logging level into the library logging object.
    log_obj = get_logger()
    log_obj.setLevel(level)

    # Add handlers for the optional screen and file output.
    fmt = '%(asctime)s %(levelname)s %(module)s: %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(fmt, datefmt)

    if screen:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        log_obj.addHandler(handler)

    if file:
        # Use a watched file handler - that way LINUX system log
        # rotation works properly.
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
        self._ui_handler = None

    #-----------------------------------------------------------------------
    def ui(self, msg, *args, **kwargs):
        """TODO: doc
        """
        if self.isEnabledFor(UI_LEVEL):
            self._log(UI_LEVEL, msg, args, **kwargs)

    #-----------------------------------------------------------------------
    def set_ui_callback(self, callback):
        """TODO: doc
        """
        self._ui_handler = CallbackHandler(callback)
        self.addHandler(self._ui_handler)

    #-----------------------------------------------------------------------
    def del_ui_callback(self):
        """TODO: doc
        """
        self.removeHandler(self._ui_handler)

    #-----------------------------------------------------------------------

#===========================================================================


class CallbackHandler(logging.Handler):
    """TODO: doc
    """
    def __init__(self, callback):
        super().__init__(UI_LEVEL)
        self.callback = callback

    #-----------------------------------------------------------------------
    def emit(self, record):
        """TODO: doc
        """
        self.callback(record)

#===========================================================================
