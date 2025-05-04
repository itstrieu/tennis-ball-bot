import logging


class Logger:
    """
    Logger class to centralize logging configuration.

    This class allows you to create loggers for different components/modules of the system.
    It supports logging to both console and a log file.
    """

    # Class-level logger instances
    _loggers = {}

    @classmethod
    def get_logger(cls, name="default", log_level=logging.INFO, log_to_file=True):
        """
        Get or create a logger instance for the given name.

        Parameters:
        - name: Name of the logger (default "default"). Typically, use the component name (e.g., "motion", "sensor").
        - log_level: The logging level (e.g., logging.INFO, logging.DEBUG). Defines which log messages are shown.
        - log_to_file: Whether to log to a file (default True). If False, only console logging will occur.
        """
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(log_level)

            # Stream handler (console logging)
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] %(message)s"
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

            # Optional: File handler (file logging)
            if log_to_file:
                file_handler = logging.FileHandler(f"{name}_log.txt")
                file_handler.setFormatter(console_formatter)
                logger.addHandler(file_handler)

            cls._loggers[name] = logger
        return cls._loggers[name]

    def __init__(self, name="default", log_level=logging.INFO, log_to_file=True):
        """
        Initialize the Logger instance.

        Parameters:
        - name: Name of the logger (default "default"). Typically, use the component name (e.g., "motion", "sensor").
        - log_level: The logging level (e.g., logging.INFO, logging.DEBUG). Defines which log messages are shown.
        - log_to_file: Whether to log to a file (default True). If False, only console logging will occur.
        """
        self.logger = self.__class__.get_logger(name, log_level, log_to_file)

    def get_instance_logger(self):
        """
        Return the logger instance.

        This allows you to use the same logger across different modules.
        """
        return self.logger

    # Future Enhancements:
    # TODO: Add functionality to support different log outputs (e.g., cloud logging or remote logging)
    # TODO: Allow the user to configure log rotation for log files (so they don't grow too large)
    # TODO: Add an option to log messages with different formats (e.g., JSON format for structured logging)
    # TODO: Implement exception logging and stack trace handling
