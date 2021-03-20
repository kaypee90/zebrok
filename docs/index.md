# Welcome to Zebrok

Zebrok is a brokerless task queue for python built on ZeroMq

It brings onboard easy implementation of efficient asynchronous processing of heavy and long running tasks without having to spin up a broker like redis, rabbitmq etc.
Zebrok takes care of all low level socket connections and data exchanges.

It is well architectured enough to support python web frameworks like Tornado, FastApi, Flask, Django and more.

Zebrok has been tested on a container orchestration platform like k8s and it works fine and also supports multiple replicas.

- Zebrok library comes with the benefits of ZeroMq, that is:
     - Low Latency
     - Lightweight
     - No broker required
     - Fast
     - Open source and more


Install using the command: `pip install git+https://github.com/kaypee90/zebrok.git#egg=zebrok`

Opened to contributions on Github
