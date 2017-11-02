class DependencyNotFoundError(KeyError):
    """ The dependency could not be found"""


class DependencyInstantiationError(TypeError):
    """ The dependency could not be instantiated """


class DependencyDuplicateError(ValueError):
    """ A dependency already exists with the same id """
