import contextlib
import threading
from collections import OrderedDict
from typing import Any, Union, Mapping, Iterable

from .stack import InstantiationStack
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
    requiring a :py:class:`~Dependency` or using :py:meth:`~provide`.

    Neither :code:`__contains__()` nor :code:`__delitem__()` are implemented as
    they are error-prone, they would only operate on the cache, not the set of
    available dependencies.
    """

    def __init__(self):
        self.providers = OrderedDict()
        self._cache = {}
        self._cache_lock = threading.RLock()
        self._instantiation_stack = InstantiationStack()

    def __str__(self):
        return "{}(providers=({}))".format(
            type(self).__name__,
            ", ".join("{}={}".format(name, p)
                      for name, p in self.providers.items()),
        )

    def __repr__(self):
        return "{}(providers=({}), cache={!r})".format(
            type(self).__name__,
            ", ".join("{!r}={!r}".format(name, p)
                      for name, p in self.providers.items()),
            self._cache
        )

    def __getitem__(self, dependency):
        """
        Get the specified dependency. :code:`item` is either the dependency_id
        or a :py:class:`~Dependency` instance in order to provide additional
        arguments to the providers.
        """
        try:
            return self._cache[dependency]
        except KeyError:
            pass

        try:
            with self._cache_lock, \
                    self._instantiation_stack.instantiating(dependency):
                try:
                    return self._cache[dependency]
                except KeyError:
                    pass

                for provider in self.providers.values():
                    try:
                        instance = provider.__antidote_provide__(
                            dependency
                            if isinstance(dependency, Dependency) else
                            Dependency(dependency)
                        )  # type: Instance
                    except DependencyNotProvidableError:
                        pass
                    else:
                        if instance.singleton:
                            self._cache[dependency] = instance.item

                        return instance.item

        except DependencyCycleError:
            raise

        except Exception as e:
            raise DependencyInstantiationError(dependency) from e

        raise DependencyNotFoundError(dependency)

    def provide(self, *args, **kwargs):
        """
        Utility method which creates a :py:class:`~Dependency` and passes it to
        :py:meth:`~__getitem__`.
        """
        return self[Dependency(*args, **kwargs)]

    def __setitem__(self, dependency_id, dependency):
        """
        Set a dependency in the cache.
        """
        with self._cache_lock:
            self._cache[dependency_id] = dependency

    def update(self, *args, **kwargs):
        """
        Update the cached dependencies.
        """
        with self._cache_lock:
            self._cache.update(*args, **kwargs)

    @contextlib.contextmanager
    def context(self,
                dependencies: Union[Mapping, Iterable] = None,
                include: Iterable = None,
                exclude: Iterable = None,
                missing: Iterable = None
                ):
        """
        Creates a context within one can control which of the defined
        dependencies available or not. Any changes will be discarded at the
        end.

        Args:
            dependencies: Dependencies instances used to override existing ones
                in the new context.
            include: Iterable of dependency to include. If None
                everything is accessible.
            exclude: Iterable of dependency to exclude.
            missing: Iterable of dependency which should raise a
                :py:exc:`~.exceptions.DependencyNotFoundError` even if a
                provider could instantiate them.

        """

        with self._cache_lock:
            original_cache = self._cache

            if missing:
                missing = set(missing)
                exclude = set(exclude) | missing if exclude else missing

                class Cache(dict):
                    def __missing__(self, key):
                        if key in missing:
                            raise DependencyNotFoundError(key)

                        raise KeyError(key)

                self._cache = Cache(original_cache if not include else {})

            elif include is None:
                self._cache = original_cache.copy()
            else:
                self._cache = {}

            if include:
                for dependency in include:
                    self._cache[dependency] = original_cache[dependency]

            if exclude:
                for dependency in exclude:
                    try:
                        del self._cache[dependency]
                    except KeyError:
                        pass

            if dependencies:
                self._cache.update(dependencies)

        try:
            yield
        finally:
            with self._cache_lock:
                self._cache = original_cache


class Dependency:
    """
    Simple container which can be used to specify a dependency ID with
    additional arguments, :code:`args` and :code:`kwargs`, for the provider.

    If no additional arguments are provided it is equivalent to the unwrapped
    dependency id.

    >>> from antidote import antidote, Dependency
    >>> antidote.container['name'] = 'Antidote'
    >>> antidote.container[Dependency('name')]
    'Antidote'

    """
    __slots__ = ('id', 'args', 'kwargs')

    def __init__(self, *args, **kwargs):
        self.id = args[0]
        assert not isinstance(self.id, Dependency)
        self.args = args[1:]
        self.kwargs = kwargs

    def __repr__(self):
        return "{}({!r}, *{!r}, **{!r})".format(
            type(self).__name__,
            self.id,
            self.args,
            self.kwargs
        )

    def __hash__(self):
        if self.args or self.kwargs:
            try:
                # Try most precise hash first
                return hash((
                    self.id,
                    self.args,
                    tuple(self.kwargs.items())
                ))
            except TypeError:
                # If type error, return the best error-free hash possible
                return hash((
                    self.id,
                    len(self.args),
                    tuple(self.kwargs.keys())
                ))

        return hash(self.id)

    def __eq__(self, other):
        return (
            (
                not self.kwargs and not self.args
                and (self.id is other or self.id == other)
            )
            or (
                isinstance(other, Dependency)
                and (self.id is other.id or self.id == other.id)
                and self.args == other.args
                and self.kwargs == other.kwargs
            )
        )


class Instance:
    """
    Simple wrapper which has to be used by providers when returning an
    instance of a dependency.

    This enables the container to know if the returned dependency needs to
    be cached or not (singleton).
    """

    __slots__ = ('item', 'singleton')

    def __init__(self, item: Any, singleton: bool = False) -> None:
        self.item = item
        self.singleton = singleton

    def __repr__(self):
        return "{}(instance={!r}, singleton={!r})".format(
            type(self).__name__,
            self.item,
            self.singleton
        )
