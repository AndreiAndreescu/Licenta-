import logging
from pythonjsonlogger import jsonlogger


def setup_logging(service_name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(service_name)
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(fmt="%(asctime)s %(name)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    return logger
