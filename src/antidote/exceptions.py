class AntidoteError(Exception):
    """ Base class of all errors of antidote. """


class DependencyDuplicateError(ValueError, AntidoteError):
    """
    A dependency already exists with the same id.
    *May* be raised by providers.
    """


class DependencyInstantiationError(TypeError, AntidoteError):
    """
    The dependency could not be instantiated.
    Raised by the container.
    """


class DependencyCycleError(RuntimeError, AntidoteError):
    """
    A dependency cycle is found.
    Raised by the container.
    """


class DependencyNotProvidableError(LookupError, AntidoteError):
    """
    The dependency could not be provided.
    Raised by providers.
    """


class DependencyNotFoundError(KeyError, AntidoteError):
    """
    The dependency could not be found in the container.
    Raised by the container.
    """
