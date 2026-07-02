import logging
import os


def create_log(name):
    """
    Create a persistent file-based log for protocol states.

    Recovery is not implemented in this lab, but writing protocol states to disk
    makes state transitions observable and keeps the structure aligned with 2PC.
    """
    logger = logging.getLogger(str(name))

    path = os.path.join(
        os.path.join(os.path.dirname(__file__), "stablelogs"),
        str(name) + ".log"
    )

    logger.addHandler(logging.FileHandler(path))
    logger.setLevel(logging.INFO)
    return logger
