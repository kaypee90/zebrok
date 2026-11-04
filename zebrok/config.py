# Author: Kaypee90 Configuration File
#
# Default settings. Each value can be overridden with the environment
# variable named in the comment next to it.

WORKER_PORT = 5690  # WORKER_PORT
WORKER_HOST = "localhost"  # WORKER_HOST

# Name of the module scanned when auto discovery is enabled.
TASKS_MODULE = "tasks"  # ZEBROK_TASKS_MODULE

# How long (in milliseconds) a publisher waits to reach a worker and to flush
# the message before giving up. Prevents publishers from hanging forever when
# no worker is running.
PUBLISH_TIMEOUT_MS = 5000  # ZEBROK_PUBLISH_TIMEOUT_MS

LOG_LEVEL = "INFO"  # ZEBROK_LOG_LEVEL
LOG_FILE = ""  # ZEBROK_LOG_FILE (empty means log to the console only)

# How often (in milliseconds) worker loops wake up to check for a stop request.
WORKER_POLL_INTERVAL_MS = 200
