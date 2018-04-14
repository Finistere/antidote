import threading
from collections import OrderedDict
from typing import Any, Dict

from .stack import DependencyStack
from ..exceptions import (
    DependencyCycleError, DependencyInstantiationError,
    DependencyNotFoundError, DependencyNotProvidableError
)
_SENTINEL = object()


class DependencyContainer:
    """
    Container of dependencies which are instantiated lazily by providers.
    Singleton are cached to ensure they're not rebuilt more than once.

    One can specify additional arguments on how to build a dependency, by
    requiring a :py:class:`~Prepare` or using :py:meth:`~provide`.

    Neither :code:`__contains__()` nor :code:`__delitem__()` are implemented as
    they are error-prone, they would only operate on the cache, not the set of
    available dependencies.
    """

    def __init__(self):
        self.providers = OrderedDict()
        self._cache = {}
        self._instantiation_lock = threading.RLock()
        self._instantiation_stack = DependencyStack()

    def __repr__(self):
        return "{}(providers=({}), cache={!r})".format(
            type(self).__name__,
            ", ".join("{!r}={!r}".format(name, p)
                      for name, p in self.providers.items()),
            self._cache
        )

    def __getitem__(self, item):
        """
        Get the specified dependency. :code:`item` is either the dependency_id
        or a :py:class:`~Prepare` instance in order to provide additional
        arguments to the providers.
        """
        try:
            return self._cache[item]
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
                if item in self._cache:
                    return self._cache[item]

                for provider in self.providers.values():
                    try:
                        dependency = provider.__antidote_provide__(*args,
                                                                   **kwargs)
                    except DependencyNotProvidableError:
                        pass
                    else:
                        if dependency.singleton:
                            self._cache[item] = dependency.instance

                        return dependency.instance

        except DependencyCycleError:
            raise

        except Exception as e:
            raise DependencyInstantiationError(item) from e

        raise DependencyNotFoundError(item)

    def provide(self, dependency_id, *args, **kwargs):
        """
        Utility method which creates a :py:class:`~Prepare` and passes it to
        :py:meth:`~__getitem__`.
        """
        return self[Prepare(dependency_id, *args, **kwargs)]

    def __setitem__(self, dependency_id, dependency):
        """
        Set a dependency in the cache.
        """
        self._cache[dependency_id] = dependency

    def update(self, dependencies: Dict):
        """
        Update the cached dependencies.
        """
        self._cache.update(dependencies)


class Prepare(object):
    """
    Simple container which can be used to specify a dependency ID with
    additional arguments, :code:`args` and :code:`kwargs`, for the provider.

    If no additional arguments are provided it is equivalent to the unwrapped
    dependency id.

    >>> from antidote import antidote, Prepare
    >>> antidote.container['name'] = 'Antidote'
    >>> antidote.container[Prepare('name')]
    'Antidote'

    """
    __slots__ = ('dependency_id', 'args', 'kwargs')

    def __init__(self, dependency_id, *args, **kwargs):
        self.dependency_id = dependency_id
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        return "{}({!r}, *{!r}, **{!r})".format(
            type(self).__name__,
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


class Dependency(object):
    """
    Simple wrapper which has to be used by providers when returning an
    instance of a dependency.

    This enables the container to know if the returned dependency needs to
    be cached or not (singleton).
    """

    __slots__ = ('instance', 'singleton')

    def __init__(self, instance: Any, singleton: bool = False) -> None:
        self.instance = instance
        self.singleton = singleton

    def __repr__(self):
        return "{}(instance={!r}, singleton={!r})".format(
            type(self).__name__,
            self.instance,
            self.singleton
        )
