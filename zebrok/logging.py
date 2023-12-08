import logging


def create_logger(module_name: str) -> logging.Logger:
    """
    Initializes a new logger object
    parameters:
        module_name (str): name of module importing the logger
    """

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(name)s %(levelname)s:%(message)s",
    )
    log_handler = logging.StreamHandler()
    log_file_handler = logging.FileHandler("zebrok.log")
    logger = logging.getLogger(module_name)
    logger.addHandler(log_handler)
    logger.addHandler(log_file_handler)
    return logger
