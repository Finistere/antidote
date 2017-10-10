class UnregisteredServiceError(KeyError):
    """ The service could not be found"""


class ServiceInstantiationError(TypeError):
    """ The service could not be instantiated """


class DuplicateServiceError(ValueError):
    """ A service already exists with the same name """
