class UnregisteredDependencyError(KeyError):
    """ The dependency could not be found"""


class DependencyInstantiationError(TypeError):
    """ The dependency could not be instantiated """


class DuplicateDependencyError(ValueError):
    """ A dependency already exists with the same id """
