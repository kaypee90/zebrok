import importlib

tasks = importlib.import_module("tasks", package='zebrok')
task = 'greet'
task_kwargs = { 
    "firstname": "Test",
    "lastname": "Lastname"
}
getattr(tasks, task)(**task_kwargs)