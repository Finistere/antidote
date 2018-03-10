import threading
from typing import Any, Dict

from collections import OrderedDict
from future.utils import raise_from

from .stack import DependencyStack
from ..exceptions import (
    DependencyCycleError, DependencyInstantiationError,
    DependencyNotFoundError, DependencyNotProvidableError
)


class Prepare(object):
    __slots__ = ('dependency_id', 'args', 'kwargs')

    def __init__(self, dependency_id, *args, **kwargs):
        self.dependency_id = dependency_id
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        return "Compose({!r}, *{!r}, **{!r})".format(
            self.dependency_id,
            self.args,
            self.kwargs
        )

    def __hash__(self):
        if len(self.args) or len(self.kwargs):
            return hash((
                self.dependency_id,
                self.args,
                tuple(self.kwargs.items())
            ))

        return hash(self.dependency_id)

    def __eq__(self, other):
        if isinstance(other, Prepare):
            return (
                self.dependency_id == other.dependency_id
                and self.args == other.args
                and self.kwargs == other.kwargs
            )
        elif not len(self.args) and not len(self.kwargs):
            return self.dependency_id == other

        return False


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

    def __getitem__(self, item):
        """
        Retrieves the dependency from the cached dependencies. If none matches,
        the container tries to find a matching factory or a matching value in
        the added dependencies.
        """
        try:
            return self._data[item]
        except KeyError:
            pass

        if isinstance(item, Prepare):
            args = (item.dependency_id,) + item.args
            kwargs = item.kwargs
        else:
            args = (item,)
            kwargs = {}

        try:
            with self._instantiation_lock, \
                    self._instantiation_stack.instantiating(item):
                if item in self._data:
                    return self._data[item]

                for provider in self.providers.values():
                    try:
                        dependency = provider.__antidote_provide__(*args,
                                                                   **kwargs)
                    except DependencyNotProvidableError:
                        pass
                    else:
                        if dependency.singleton:
                            self._data[item] = dependency.instance

                        return dependency.instance

        except DependencyCycleError:
            raise

        except Exception as e:
            raise_from(DependencyInstantiationError(item), e)

        raise DependencyNotFoundError(item)

    def __setitem__(self, dependency_id, dependency):
        """
        Set a dependency in the cache.
        """
        self._data[dependency_id] = dependency

    def provide(self, dependency_id, *args, **kwargs):
        return self[Prepare(dependency_id, *args, **kwargs)]

    def update(self, dependencies):
        # type: (Dict) -> None
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

    __slots__ = ('instance', 'singleton')

    def __init__(self, instance, singleton=False):
        # type: (Any, bool) -> None
        self.instance = instance
        self.singleton = singleton
