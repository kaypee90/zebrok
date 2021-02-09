import logging


def create_logger(module_name):
    logging.basicConfig(
                        level=logging.DEBUG,
                        format="%(asctime)s %(name)s %(levelname)s:%(message)s"
                        )
    log_handler = logging.StreamHandler()
    logger = logging.getLogger(module_name)
    logger.addHandler(log_handler)
    return logger
