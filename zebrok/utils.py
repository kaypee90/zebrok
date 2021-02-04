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
    port, host = __get_worker_port_and_host()
    socket_address = f"tcp://127.0.0.1:{str(port)}"

    if not worker:
        socket_address = f"tcp://{host}:{str(port)}"
    
    logger.info(f"Connecting on {socket_address}")
    return socket_address

def __get_worker_port_and_host():
    '''
    Retrieves port number and the host worker will 
    be listening on configuration
    '''
    port = None
    host = None
    
    try:
        from django.conf import settings
        if not port:
            port = settings.WORKER_PORT

        if not host:
            host = settings.WORKER_HOST
    except Exception:
        logger.warning("Attempt to load from django settings failed!")

    if not port:
        port = os.environ.get("WORKER_PORT")

    if not host:
        host = os.environ.get("WORKER_HOST")
    
    # Load default values
    if not port:
        from .config import WORKER_PORT
        port = WORKER_PORT
        
    if not host:
        from .config import WORKER_HOST
        host = WORKER_HOST   

    return port, host

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



