import importlib


def get_discovered_task_by_name(task_name):
    """
    Finds declared tasks
    """
    try:
        tasks = importlib.import_module("tasks", package="zebrok")
    except ModuleNotFoundError:
        return None
    return getattr(tasks, task_name)
