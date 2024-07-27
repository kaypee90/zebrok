import logging


def create_logger(module_name: str) -> "logging.Logger":
    """
    Initializes a new logger object
    parameters:
        module_name (str): name of module importing the logger
    """
    logger = logging.getLogger(module_name)
    logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    file_handler = logging.FileHandler("zebrok.log")

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    formatter = logging.Formatter(
        "{asctime} - {name} - {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    return logger
