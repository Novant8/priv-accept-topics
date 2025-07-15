import logging

class Logger(logging.Logger):
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)

        colored_handler = logging.StreamHandler()
        colored_handler.setFormatter(self.ColoredFormatter('%(message)s'))

        self.setLevel(global_level or logging.INFO)
        self.handlers = []
        self.addHandler(self.ListHandler())
        self.addHandler(colored_handler)

    class ListHandler(logging.Handler):
            records: list[logging.LogRecord]

            def __init__(self):
                super().__init__()
                self.records = []

            def emit(self, record):
                self.records.append(record)

    class ColoredFormatter(logging.Formatter):
        COLORS = {
            logging.DEBUG: "\033[30m",    # Black
            logging.INFO: "\033[36m",     # Cyan
            logging.WARNING: "\033[33m",  # Yellow
            logging.ERROR: "\033[31m",    # Red
            logging.CRITICAL: "\033[41m", # Red + background
        }
        BOLD = "\033[1m"
        RESET_BOLD = "\033[22m"
        WHITE = "\033[37m"
        RESET_ALL = "\033[0m"

        def format(self, record):
            record.asctime = self.formatTime(record, self.datefmt)
            level_color = self.COLORS.get(record.levelno, self.RESET_ALL)
            formatted = super().format(record)
            return f"{level_color}[{self.BOLD}{level_color}{record.levelname}{self.RESET_BOLD} - {record.asctime}] {formatted}{self.RESET_ALL}"

LOG_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

def getLogLevel(name: str):
    return LOG_MAP[name]

global_level = None
def setup_logging(level=logging.INFO):
    for logger in logging.root.manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            logger.setLevel(level)

    global global_level
    global_level = level

def getLogger(name: str):
    return logging.getLogger(name)

def getAllLoggerEntries() -> list[str]:
    records = [
        record
        for logger in logging.root.manager.loggerDict.values()
            if isinstance(logger, logging.Logger)
        for handler in logger.handlers
            if isinstance(handler, Logger.ListHandler)
        for record in handler.records
    ]
    formatter = logging.Formatter('[%(levelname)s - %(asctime)s] %(message)s')
    return [ formatter.format(record) for record in sorted(records, key=lambda r: r.created) ]

logging.setLoggerClass(Logger)