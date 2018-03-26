import logging

# Set up the default logger. We only want the message itself.
_log_fmt_string = '%(levelname)s: %(message)s'
_log_formatter = logging.Formatter(fmt=_log_fmt_string)
root_logger = logging.getLogger()
_stderr_handler = logging.StreamHandler()
_stderr_handler.setFormatter(_log_formatter)
root_logger.addHandler(_stderr_handler)
root_logger.setLevel(logging.WARNING)
