import importlib
from typing import Any
from typing import Callable
from typing import Optional

from zebrok.config import TASK_TYPE
from zebrok.logging import create_logger

logger = create_logger(__name__)


def get_import_module() -> Any:
    """
    Used for dynamic import of tasks
    """
    return importlib.import_module("tasks", package="zebrok")


def get_discovered_task_by_name(task_name: str) -> Optional[Callable[..., Any]]:
    """
    Finds declared tasks
    """
    task = None
    try:
        tasks = get_import_module()
        task = getattr(tasks, task_name)
    except (ModuleNotFoundError, AttributeError) as e:
        logger.error(e)
    return task


# TODO: Improve this process to be efficient
def discover_tasks() -> int:
    tasks_module = get_import_module()
    task_names = []
    for task_name in dir(tasks_module):
        task = getattr(tasks_module, task_name)
        if str(task).startswith(f"<{TASK_TYPE}"):
            task_names.append(f"\n  * {task_name} ")
    no_of_tasks = len(task_names)
    line_separator = "\n====================================================="
    heading = f"** {no_of_tasks} ZEBROK TASKS DISCOVERED! {line_separator}"

    task_names_str = "".join([heading] + task_names + [line_separator])
    logger.info(task_names_str)
    return no_of_tasks
