class UndefinedServiceError(LookupError):
    """ The service could not be found"""


class ServiceInstantiationError(RuntimeError):
    """ The service could not be instantiated """


class DuplicateServiceError(ValueError):
    """ A service already exists with the same name """
