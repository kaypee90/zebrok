FROM python:3.13-slim-bookworm

# WORKER_HOST=* makes a worker listen on all interfaces. Containers that
# publish tasks must override it with the worker's host name
# (docker-compose.yml sets WORKER_HOST=worker for both services).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    WORKER_HOST=* \
    WORKER_PORT=5690

RUN useradd --create-home --uid 1000 zebrok

WORKDIR /code

# Install the library first so this layer is cached across code-only changes.
COPY setup.py README.md LICENSE MANIFEST.in /code/
COPY zebrok /code/zebrok
RUN pip install .

COPY --chown=zebrok . /code/
USER zebrok

EXPOSE 5690

# Starts the example worker. Override the command to run your own entrypoint.
CMD ["python", "examples/start.py"]
