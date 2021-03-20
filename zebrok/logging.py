import logging


def create_logger(module_name):
    """
    Initializes a new logger object
    """

    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s:%(message)s"
    )
    log_handler = logging.StreamHandler()
    log_file_handler = logging.FileHandler("zebrok.log")
    logger = logging.getLogger(module_name)
    logger.addHandler(log_handler)
    logger.addHandler(log_file_handler)
    return logger
