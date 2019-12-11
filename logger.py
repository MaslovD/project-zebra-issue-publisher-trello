import logging
from logging.handlers import TimedRotatingFileHandler
from config import ApplicationConfig
from os import getenv
import sys

PROPERTIES_URL = getenv('PROPERTIES_URL')
config = ApplicationConfig(PROPERTIES_URL)
FORMATTER = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(message)s")
LOG_FILE = "ipt.log"


def get_console_handler():
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    return console_handler


def get_file_handler():
    file_handler = TimedRotatingFileHandler(LOG_FILE, when='midnight')
    file_handler.setFormatter(FORMATTER)
    return file_handler


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(config.logging_level)
    logger.addHandler(get_console_handler())
    logger.addHandler(get_file_handler())
    return logger
