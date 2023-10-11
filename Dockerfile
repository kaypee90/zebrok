FROM python:3.12.0-slim-bookworm
ENV PYTHONUNBUFFERED 1

RUN mkdir /code
WORKDIR /code

COPY requirements.txt requirements-documentation.txt /code/
RUN pip install -r requirements.txt

COPY . /code/

ENTRYPOINT  sleep 365d
