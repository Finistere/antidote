class UnregisteredDependencyError(KeyError):
    """ The service could not be found"""


class DependencyInstantiationError(TypeError):
    """ The service could not be instantiated """


class DuplicateDependencyError(ValueError):
    """ A service already exists with the same name """
