class ZebrokError(Exception):
    """
    Base class for all zebrok errors
    """


class ZebrokNotImplementedError(ZebrokError, NotImplementedError):
    """
    Custom exception to be thrown when a derived class
    fails to implement an abstract method of a base class
    """


class ZebrokPublishError(ZebrokError):
    """
    Raised when a task could not be handed to a worker, for example
    because no worker is reachable before the publish timeout expires
    """
