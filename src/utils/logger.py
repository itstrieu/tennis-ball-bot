import logging


class Logger:
    """
    Logger class to centralize logging configuration.

    This class allows you to create loggers for different components/modules of the system.
    It supports logging to both console and a log file.
    """

    def __init__(self, name="default", log_level=logging.INFO, log_to_file=True):
        """
        Initialize the Logger instance.

        Parameters:
        - name: Name of the logger (default "default"). Typically, use the component name (e.g., "motion", "sensor").
        - log_level: The logging level (e.g., logging.INFO, logging.DEBUG). Defines which log messages are shown.
        - log_to_file: Whether to log to a file (default True). If False, only console logging will occur.
        """
        self.logger = logging.getLogger(
            name
        )  # TODO: Create a logger with the provided name
        self.logger.setLevel(
            log_level
        )  # TODO: Set the log level to control message verbosity

        # Stream handler (console logging)
        console_handler = logging.StreamHandler()  # TODO: Handle log output to console
        console_formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s"
        )  # TODO: Format the log messages for better readability
        console_handler.setFormatter(
            console_formatter
        )  # TODO: Attach the formatter to the handler
        self.logger.addHandler(
            console_handler
        )  # TODO: Add the console handler to the logger

        # Optional: File handler (file logging)
        if log_to_file:
            file_handler = logging.FileHandler(
                f"{name}_log.txt"
            )  # TODO: Log to file with the given file name
            file_handler.setFormatter(
                console_formatter
            )  # TODO: Use the same log format for file output
            self.logger.addHandler(
                file_handler
            )  # TODO: Add the file handler to the logger

    def get_logger(self):
        """
        Return the logger instance.

        This allows you to use the same logger across different modules.
        """
        # TODO: Return the logger instance so it can be used elsewhere in the project
        return self.logger

    # Future Enhancements:
    # TODO: Add functionality to support different log outputs (e.g., cloud logging or remote logging)
    # TODO: Allow the user to configure log rotation for log files (so they don't grow too large)
    # TODO: Add an option to log messages with different formats (e.g., JSON format for structured logging)
    # TODO: Implement exception logging and stack trace handling
