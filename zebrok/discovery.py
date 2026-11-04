import importlib
from types import ModuleType

from .app import Task
from .logging import create_logger
from .utils import get_tasks_module_name

logger = create_logger(__name__)


def get_import_module() -> ModuleType | None:
    """
    Imports the tasks module (ZEBROK_TASKS_MODULE, default "tasks").
    Returns None if that module does not exist.
    """
    module_name = get_tasks_module_name()
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        # Only swallow "the tasks module is missing"; a missing import
        # *inside* the tasks module is a real bug and must surface.
        missing = e.name or ""
        if module_name != missing and not module_name.startswith(missing + "."):
            raise
        logger.warning(f"Tasks module '{module_name}' not found for auto discovery")
        return None


def get_discovered_task_by_name(task_name: str) -> Task | None:
    """
    Finds a task declared in the tasks module.

    Only objects decorated with @Task are returned, so a remote message can't
    invoke arbitrary callables that happen to live in the module (imported
    helpers, modules, builtins, ...).
    """
    tasks_module = get_import_module()
    if tasks_module is None:
        return None
    task = getattr(tasks_module, task_name, None)
    if task is None:
        logger.error(f"No task named '{task_name}' in module '{tasks_module.__name__}'")
        return None
    if not isinstance(task, Task):
        logger.error(f"Refusing to run '{task_name}': it is not decorated with @Task")
        return None
    return task


def discover_tasks() -> int:
    """
    Logs and counts the tasks declared in the tasks module
    """
    tasks_module = get_import_module()
    if tasks_module is None:
        return 0
    task_names = sorted(
        name for name, obj in vars(tasks_module).items() if isinstance(obj, Task)
    )
    line_separator = "\n====================================================="
    heading = f"** {len(task_names)} ZEBROK TASKS DISCOVERED! {line_separator}"
    listing = "".join(f"\n  * {name} " for name in task_names)
    logger.info(f"{heading}{listing}{line_separator}")
    return len(task_names)
