class DependencyError(Exception):
    """ Base class of all errors of antidote. """


class DependencyDuplicateError(ValueError, DependencyError):
    """ A dependency already exists with the same id. """


class DependencyInstantiationError(TypeError, DependencyError):
    """ The dependency could not be instantiated. """


class DependencyCycleError(RuntimeError, DependencyError):
    """ A dependency cycle is found. """


class DependencyNotProvidableError(LookupError, DependencyError):
    """ The dependency could not be instantiated by a providers. """


class DependencyNotFoundError(KeyError, DependencyError):
    """ The dependency could not be found in the container. """
