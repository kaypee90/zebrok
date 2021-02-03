import os
import json
import logging

logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s %(name)s %(levelname)s:%(message)s')
logHandler = logging.StreamHandler()
logger = logging.getLogger(__name__)
logger.addHandler(logHandler)

def get_socket_address_from_conf(worker=False):
    '''
    Retrieves socket address configuration
    '''
    socket_address = None
    
    try:
        from django.conf import settings
        if not socket_address and worker:
            socket_address = settings.ZMQ_WORKER_ADDR

        if not socket_address and not worker:
            socket_address = settings.ZMQ_ADDR
    except Exception:
        logger.warning("Attempt to load from django settings failed!")

    if not socket_address and worker:
        socket_address = os.environ.get("ZMQ_WORKER_ADDR")

    if not socket_address and not worker:
        socket_address = os.environ.get("ZMQ_ADDR")
    
    try:
        if worker:
            from .config import ZMQ_WORKER_ADDR
            socket_address = ZMQ_WORKER_ADDR
        else:
            from .config import ZMQ_ADDR
            socket_address = ZMQ_ADDR
    except ImportError:
        logger.warning("No config file found!")

    logger.info(f"Connection on {socket_address}")

    return socket_address

def pickle_task(task_obj):
    '''
    Convert task dict to a json string
    '''
    return json.dumps(task_obj)

def unpickle_task(task_str):
    '''
    Convert json string representation of a tasks
     dict to a python dict
    '''
    logger.info("Received task!")
    return json.loads(task_str)



