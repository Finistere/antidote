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

    A dependency can be retrieved through its name. The type of the dependency
    is used as its name when registering a factory.

    The container uses a cache to instantiate lazily dependencies, deleting and
    setting dependencies only affects the cache, not the registered nor
    user-added dependencies. However, checking whether a dependency is defined
    will search in the cache, the registered and user-added dependencies.
    """
    def __init__(self):
        self._cache = {}
        self._dependency_factories_by_type = dict()
        # Elements in _factories must be either the dependencies themselves or
        # their factory.
        self._factories = ChainMap(self._dependency_factories_by_type)
        self._instantiation_lock = threading.RLock()

    def __getitem__(self, name):
        """
        Retrieves the service from the instantiated services. If no service
        matches, the container tries to find one which can be instantiated.
        """
        try:
            return self._cache[name]
        except KeyError:
            try:
                factory = self._factories[name]
            except KeyError:
                raise UnregisteredDependencyError(name)

        try:
            try:
                if not factory.singleton:
                    return factory()
            except AttributeError:
                pass

            if callable(factory):
                with self._instantiation_lock:
                    if name not in self._cache:
                        self._cache[name] = factory()
            else:
                self._cache[name] = factory

        except Exception as e:
            raise DependencyInstantiationError(repr(e))

        return self._cache[name]

    def __setitem__(self, name, dependency):
        self._cache[name] = dependency

    def __delitem__(self, name):
        try:
            del self._cache[name]
        except KeyError:
            if name not in self._factories:
                raise UnregisteredDependencyError(name)

    def __contains__(self, name):
        return name in self._cache or name in self._factories

    def register(self, factory, type=None, singleton=True):
        """Register a dependency factory by the type of the dependency.

        Args:
            factory (callable): Callable to be used to instantiate the
                dependency.
            type (type, optional): Type of the dependency, by which it is
                identified. Defaults to the type of the factory.
            singleton (bool, optional): A singleton will be only be
                instantiated once. Otherwise the dependency will instantiated
                anew every time.
        """
        type = type or factory
        dependency_factory = DependencyFactory(factory=factory,
                                               singleton=singleton)

        if type in self._dependency_factories_by_type:
            raise DuplicateDependencyError(type)

        self._dependency_factories_by_type[type] = dependency_factory

    def deregister(self, type):
        """Deregister a dependency factory by the type of the dependency.

        Args:
            type (type, optional): Type of the dependency.

        """
        try:
            del self._dependency_factories_by_type[type]
        except KeyError:
            raise UnregisteredDependencyError(type)

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
