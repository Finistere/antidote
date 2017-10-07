from .exceptions import *

try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap


class Container:
    """
    Container of services and parameters. Those are either retrieved by their
    type (typically services class) or by a user-provided id.
    The user id has always the priority.

    Services are instantiated lazily, only on demand.
    """
    def __init__(self):
        self._services_cache = {}
        self._services_by_type = dict()
        self.services = ChainMap(self._services_by_type)

    def __getitem__(self, item):
        """
        Retrieves the service from the instantiated services. If no service
        matches, the container tries to find one which can be instantiated.
        """
        try:
            return self._services_cache[item]
        except KeyError:
            try:
                service = self.services[item]
            except KeyError:
                raise UnregisteredServiceError(item)
            else:
                if isinstance(service, Service):
                    try:
                        instance = service.factory()
                    except Exception as e:
                        raise ServiceInstantiationError(repr(e))
                    else:
                        if service.singleton:
                            self._services_cache[item] = instance
                        return instance
                else:
                    self._services_cache[item] = service
                    return service

    def __setitem__(self, key, value):
        self._services_cache[key] = value

    def __delitem__(self, key):
        try:
            del self._services_cache[key]
        except KeyError:
            if key not in self.services:
                raise UnregisteredServiceError(key)

    def __contains__(self, item):
        return item in self._services_cache or item in self.services

    def register(self, factory, type=None, singleton=True):
        """
        Register a service in the container.
        """
        type = type or factory
        service = Service(factory=factory, singleton=singleton)

        if type in self._services_by_type:
            raise DuplicateServiceError(type)

        self._services_by_type[type] = service

    def deregister(self, type):
        try:
            del self._services_by_type[type]
        except KeyError:
            raise UnregisteredServiceError(type)

    def append(self, services):
        """
        Extend the current container with another one.
        """
        self.services.maps.append(services)

    def prepend(self, services):
        """
        Extend the current container with another one.
        """
        self.services = self.services.new_child(services)


class Service:
    __slots__ = ('factory', 'singleton')

    def __init__(self, factory, singleton):
        self.factory = factory
        self.singleton = singleton
