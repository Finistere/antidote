import threading
from .exceptions import *

try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap


class DependencyContainer:
    """
    Container of dependencies. Dependencies are either factories which must be
    registered or any user-given data.

    A dependency can be retrieved through its id. The factory of the
    dependency itself is used as its id if none is provided.

    The container uses a cache to instantiate lazily dependencies, deleting and
    setting dependencies only affects the cache, not the registered nor
    user-added dependencies. However, checking whether a dependency is defined
    will search in the cache, the registered and user-added dependencies.
    """

    def __init__(self):
        self._cache = {}
        self._registered_factories = dict()
        # Elements in _factories must be either the dependencies themselves or
        # their factory.
        self._factories = ChainMap(self._registered_factories)
        self._instantiation_lock = threading.RLock()

    def __getitem__(self, id):
        """
        Retrieves the dependency from the cached dependencies. If none matches,
        the container tries to find a matching factory or a matching value in
        the added dependencies.
        """
        try:
            return self._cache[id]
        except KeyError:
            try:
                factory = self._factories[id]
            except KeyError:
                raise UnregisteredDependencyError(id)

        try:
            try:
                if not factory.singleton:
                    return factory()
            except AttributeError:
                pass

            if callable(factory):
                with self._instantiation_lock:
                    if id not in self._cache:
                        self._cache[id] = factory()
            else:
                self._cache[id] = factory

        except Exception as e:
            raise DependencyInstantiationError(repr(e))

        return self._cache[id]

    def __setitem__(self, id, dependency):
        """
        Set a dependency in the cache.
        """
        self._cache[id] = dependency

    def __delitem__(self, id):
        """
        Remove dependency from the cache. Beware that this will not remove
        registered dependencies or user-added dependencies.
        """
        try:
            del self._cache[id]
        except KeyError:
            if id not in self._factories:
                raise UnregisteredDependencyError(id)

    def __contains__(self, id):
        """
        Check whether the dependency is in the cache, the registered
        dependencies, or user-added dependencies.
        """
        return id in self._cache or id in self._factories

    def register(self, factory, id=None, singleton=True):
        """Register a dependency factory by the type of the dependency.

        Args:
            factory (callable): Callable to be used to instantiate the
                dependency.
            id (object, optional): Type of the dependency, by which it is
                identified. Defaults to the type of the factory.
            singleton (bool, optional): A singleton will be only be
                instantiated once. Otherwise the dependency will instantiated
                anew every time.
        """
        id = id or factory
        dependency_factory = DependencyFactory(factory=factory,
                                               singleton=singleton)

        if id in self._registered_factories:
            raise DuplicateDependencyError(id)

        self._registered_factories[id] = dependency_factory

    def deregister(self, id):
        """Deregister a dependency factory by the type of the dependency.

        Args:
            id (object, optional): Type of the dependency.

        """
        try:
            del self._registered_factories[id]
        except KeyError:
            raise UnregisteredDependencyError(id)

    def extend(self, dependencies):
        """Extend the container with a dictionary of default dependencies.

        The additional dependencies definitions are only used if it could not
        be found in the current container.

        Args:
            dependencies (dict): Dictionary of dependencies or their factory.

        """
        self._factories.maps.append(dependencies)

    def override(self, dependencies):
        """Override any existing definition of dependencies.

        Args:
            dependencies (dict): Dictionary of dependencies or their factory.

        """
        self._factories.maps = [dependencies] + self._factories.maps


class DependencyFactory:
    __slots__ = ('factory', 'singleton')

    def __init__(self, factory, singleton):
        self.factory = factory
        self.singleton = singleton

    def __call__(self):
        return self.factory()
