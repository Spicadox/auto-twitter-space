import logging
from logging.handlers import TimedRotatingFileHandler
import os.path
import const


# Filter subclass that does not allow the file logging of sleeping messages
class NoParsingFilter(logging.Filter):
    def filter(self, record):
        return not record.getMessage().startswith('Sleeping')


# Filter subclass to allow and not allow stack traceback filtering
class TracebackInfoFilter(logging.Filter):
    """Clear or restore the exception on log records"""
    def __init__(self, clear=True):
        self.clear = clear

    def filter(self, record):
        if self.clear:
            record._exc_info_hidden, record.exc_info = record.exc_info, None
            # clear the exception traceback text cache, if created.
            record.exc_text = None
        elif hasattr(record, "_exc_info_hidden"):
            record.exc_info = record._exc_info_hidden
            del record._exc_info_hidden
        return True


def create_logger(logfile_name):
    # Check if log dir exist and if not create it
    logging.handlers.TimedRotatingFileHandler
    log_dir = os.getcwd()+"\\logs"
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)

    # Get the logger object
    logger = logging.getLogger(__name__)

    # If logger has already been created then return it(for the imported modules)
    if len(logger.handlers) != 0:
        return logger

    # Set logging level and log path
    logger.setLevel(logging.DEBUG)
    log_path = log_dir + "\\" + logfile_name

    # Create a new log file everyday
    handler = TimedRotatingFileHandler(log_path, when="midnight", interval=1, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s [%(filename)s:%(lineno)d] %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    handler.suffix = "%Y%m%d"   # file suffix to be changed
    handler.addFilter(NoParsingFilter())
    # Set handler to allow stacktraceback logging
    handler.addFilter(TracebackInfoFilter(clear=False))

    # logging.basicConfig(level=logging.INFO,
    #                     format='%(asctime)s [%(filename)s:%(lineno)d] %(levelname)-5s %(message)s',
    #                     datefmt='%Y-%m-%d %H:%M',
    #                     filename=log_path)

    # define a Handler which writes DEBUG messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.addFilter(TracebackInfoFilter())
    # set a format which is simpler for console use
    console_formatter = logging.Formatter('[%(levelname)s] %(asctime)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    # tell the handler to use this format
    console.setFormatter(console_formatter)
    # add the handlers to the root logger
    logger.addHandler(console)
    logger.addHandler(handler)

    # If logging is not enabled then remove the root log handler but keep the stream handler
    if not const.LOGGING:
        try:
            lhStdout = logger.handlers[1]
            logger.removeHandler(lhStdout)
        except IndexError as ierror:
            logger.error(ierror)
            return logger
    return logger
