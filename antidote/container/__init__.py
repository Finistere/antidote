import threading
from collections import OrderedDict

from future.utils import raise_from

from .stack import DependencyStack
from ..exceptions import (
    DependencyNotFoundError, DependencyNotProvidableError,
    DependencyCycleError, DependencyInstantiationError
)


class DependencyContainer(object):
    """
    Container of dependencies. Dependencies are either _factories which must be
    registered or any user-given data.

    A dependency can be retrieved through its id. The factory of the
    dependency itself is used as its id if none is provided.

    The container uses a cache to instantiate lazily dependencies, deleting and
    setting dependencies only affects the cache, not the registered nor
    user-added dependencies. However, checking whether a dependency is defined
    will search in the cache, the registered and user-added dependencies.
    """

    def __init__(self):
        self.providers = OrderedDict()
        self._data = {}
        self._instantiation_lock = threading.RLock()
        self._instantiation_stack = DependencyStack()

    def __getitem__(self, dependency_id):
        """
        Retrieves the dependency from the cached dependencies. If none matches,
        the container tries to find a matching factory or a matching value in
        the added dependencies.
        """
        try:
            return self._data[dependency_id]
        except KeyError:
            pass

        try:
            with self._instantiation_lock, \
                    self._instantiation_stack.instantiating(dependency_id):
                if dependency_id in self._data:
                    return self._data[dependency_id]

                for provider in self.providers.values():
                    try:
                        dependency = provider.__antidote_provide__(
                            dependency_id
                        )
                    except DependencyNotProvidableError:
                        pass
                    else:
                        if dependency.singleton:
                            self._data[dependency_id] = dependency.instance

                        return dependency.instance

        except DependencyCycleError:
            raise

        except Exception as e:
            raise_from(DependencyInstantiationError(dependency_id), e)

        raise DependencyNotFoundError(dependency_id)

    def __setitem__(self, dependency_id, dependency):
        """
        Set a dependency in the cache.
        """
        self._data[dependency_id] = dependency

    def update(self, dependencies):
        """
        Update the cached dependencies.
        """
        self._data.update(dependencies)


class Dependency(object):
    """
    Simple wrapper which has to be used by providers when returning an
    instance of a dependency.

    This enables the container to know if the returned dependency needs to
    be cached as a singleton or not.
    """

    def __init__(self, instance, singleton=False):
        self.instance = instance
        self.singleton = singleton
