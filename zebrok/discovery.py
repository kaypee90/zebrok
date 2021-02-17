import importlib
from zebrok.logging import create_logger

logger = create_logger(__name__)


def get_discovered_task_by_name(task_name):
    """
    Finds declared tasks
    """
    task = None
    try:
        tasks = importlib.import_module("tasks", package="zebrok")
        task = getattr(tasks, task_name)
    except (ModuleNotFoundError, AttributeError) as e:
        logger.error(e)
    return task
