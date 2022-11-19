import os
import logging
from typing import Dict, Optional


def configure_logger(name: str, debug: bool = False) -> None:

    _logger = logging.getLogger(name)

    FORMATTER = logging.Formatter(
        "%(asctime)s - %(name)s:%(lineno)s - %(levelname)s - "
        "%(funcName)s - %(message)s"
    )
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(FORMATTER)

    # clear any existing handler(s) before adding new
    for handler in _logger.handlers:
        _logger.removeHandler(handler)
    _logger.addHandler(log_handler)

    if debug is True:
        _logger.setLevel(logging.DEBUG)
    else:
        _logger.setLevel(logging.WARNING)


def write_secrets_file(filepath: str, contents: bytes) -> None:
    """write file containing one or more secrets,
    directory should already be created and writeable by user,
    filepath will only have read/write permissions for user"""
    fd = os.open(filepath, os.O_WRONLY | os.O_CREAT, mode=0o600)
    os.write(fd, contents)
    os.close(fd)


def read_file(filepath: str) -> Optional[str]:
    try:
        with open(filepath, "r") as rfile:
            contents = rfile.read()
    except FileNotFoundError:
        return None
    return contents


def lower_dict_keys(input_dict: Dict[str, str]) -> Dict[str, str]:
    return dict((k.lower(), v) for k, v in input_dict.items())
