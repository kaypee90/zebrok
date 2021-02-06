import importlib

tasks = importlib.import_module("tasks", package='zebrok')


def get_discovered_task_by_name(task_name):
    return getattr(tasks, task_name)
