from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, overload, Type, TypeVar

from typing_extensions import Protocol

from .._internal import API, debug_repr
from .data import CatalogId, DependencyDebug, LifeTime

__all__ = ["Provider", "ProvidedDependency", "ProviderCatalog"]

P = TypeVar("P", bound="Provider")
Result = TypeVar("Result")


@API.public
class ProvidedDependency(Protocol):
    """
    Using by a :py:class:`.Provider` to return the value of a dependency.
    :py:meth:`.ProvidedDependency.set_value` can only be called once and will raise an error after.
    """

    @overload
    def set_value(
        self, value: Result, *, lifetime: LifeTime, callback: Callable[[], Result]
    ) -> None:
        ...

    @overload
    def set_value(self, value: object, *, lifetime: LifeTime) -> None:
        ...

    def set_value(
        self,
        value: Result,
        *,
        lifetime: LifeTime,
        callback: Callable[..., Result] | None = None,
    ) -> None:
        """
        Defines the value and the lifetime of a dependency. If a callback function is provided it
        will be used to generate the dependency value next time it's needed. For a singleton, it's
        silently ignored.

        .. warning::

            Beware that defining a callback for a transient dependency, will force Antidote to keep
            the dependency object inside its cache and as such hold a strong reference to it.

        """
        ...


@API.public
class ProviderCatalog(Protocol):
    """
    Similar interface to :py:class:`.ReadOnlyCatalog`. However, it won't use
    :py:class:`.dependencyOf` to unwrap dependencies and hence does not provide any typing. You
    should use the raw dependencies directly.
    """

    @property
    def id(self) -> CatalogId:
        ...

    def __contains__(self, dependency: object) -> bool:
        ...

    def __getitem__(self, dependency: object) -> Any:
        ...

    def get(self, dependency: object, default: object = None) -> Any:
        ...

    @property
    def is_frozen(self) -> bool:
        ...

    def raise_if_frozen(self) -> None:
        ...

    def debug(self, __obj: object, *, depth: int = -1) -> str:
        ...


@API.public
class Provider(ABC):
    """
    Antidote distinguishes two aspects of dependency management:

    - The definition of the dependency and its value, which is the responsibility of
      a :py:class:`.Provider`.
    - The lifetime management of the dependency values, including their thread-safety, which is the
      responsibility of the :py:class:`.Catalog`.

    All of Antidote's dependencies, such as :py:func:`.injectable` or :py:func:`.lazy`, rely on a
    :py:class:`.Provider` underneath. So creating a new :py:class:`.Provider` allows one to define
    a new kind of dependencies. Before diving into the implementation, there are several
    expectations from the :py:class:`.Catalog`:

    - Providers *MUST* have a distinct set of dependencies. One provider cannot shadow another one.
      Use child catalogs for this.
    - Providers *MUST NOT* store any dependency values, they're only expected to store *how*
      dependency are defined.
    - *ONLY* methods prefixed with :code:`unsafe` are called in a thread-safe manner by the
      :py:class:`.Catalog`. For all others, you must ensure thread-safety yourself.

    A :py:class:`.Provider` must implement at least two methods:

    - :py:meth:`~.Provider.can_provide` which returns whether the dependency can be provided or not.
    - :py:meth:`~.Provider.unsafe_maybe_provide` which provides the dependency value if possible.
      :py:meth:`~.Provider.can_provide` is NOT called before using this method.

    Here is a minimal example which provides the square of a number:

    .. doctest:: core_provider

        >>> from dataclasses import dataclass
        >>> from antidote.core import Provider, ProvidedDependency, world, LifeTime, Dependency
        >>> @dataclass(unsafe_hash=True)  # a dependency must be hashable
        ... class SquareOf(Dependency[int]):  # Dependency ensures proper typing with world & inject
        ...     number: int
        >>> @world.include
        ... class SquareProvider(Provider):
        ...     def can_provide(self, dependency: object) -> bool:
        ...         return isinstance(dependency, SquareOf)
        ...
        ...     def unsafe_maybe_provide(self, dependency: object, out: ProvidedDependency) -> None:
        ...         # Checking whether we can provide the dependency
        ...         if isinstance(dependency, SquareOf):
        ...             out.set_value(dependency.number ** 2, lifetime=LifeTime.TRANSIENT)
        >>> world[SquareOf(12)]
        144

    Other than those two methods, the catalog will also call the following which have a default
    implementation:

    - :py:meth:`~.Provider.create` used when including the :py:class:`.Provider` in a catalog.
    - :py:meth:`~.Provider.copy` used by :py:meth:`~.TestCatalogBuilder.copy` and
      :py:meth:`~.TestCatalogBuilder.clone` test environments.
    - :py:meth:`~.Provider.maybe_debug` used by :py:meth:`.Catalog.debug`.

    """

    __slots__ = ("_catalog",)
    _catalog: ProviderCatalog

    @classmethod
    def create(cls: Type[P], catalog: ProviderCatalog) -> P:
        """
        Used by the catalog to create an instance when using :py:meth:`.Catalog.include`.
        """
        return cls(catalog=catalog)

    def unsafe_copy(self: P) -> P:
        """
        Used for the :py:meth:`~.TestCatalogBuilder.copy` and :py:meth:`~.TestCatalogBuilder.clone`
        test environments. It should return a deep copy of the provider, changes in the copy should
        not affect the original one.
        """
        return self.create(catalog=self._catalog)

    def __init__(self, *, catalog: ProviderCatalog) -> None:
        """
        The catalog only relies on :py:meth:`~.Provider.create` and :py:meth:`~.Provider.copy` for
        instantiation, so feel free to change :code:`__init__()` however you wish.
        """
        object.__setattr__(self, "_catalog", catalog)

    def maybe_debug(self, dependency: object) -> DependencyDebug | None:
        """
        Called by :py:meth:`.Catalog.debug` to generate a debug tree. It should return a
        :py:class:`.DependencyDebug` if the dependency can be provided or :py:obj:`None` otherwise.
        By default, it will only return a description specifying that this method is not
        implemented if the dependency can be provided.

        This method *MUST* be implemented in a thread-safe manner. :py:meth:`~.Provider.can_provide`
        is not called before using this method.
        """
        if self.can_provide(dependency):
            return DependencyDebug(
                description=f"No debug provided by {debug_repr(type(self))}",
                lifetime=LifeTime.TRANSIENT,
            )
        return None

    @abstractmethod
    def can_provide(self, dependency: object) -> bool:
        """
        Should return whether the dependency can be provided or not.

        This method *MUST* be implemented in a thread-safe manner.
        """
        raise NotImplementedError()

    @abstractmethod
    def unsafe_maybe_provide(self, dependency: object, out: ProvidedDependency) -> None:
        """
        If the dependency can be provided, it should be provided through the specified
        :py:class:`.ProvidedDependency`. :py:meth:`~.Provider.can_provide` is not called before
        using this method.
        """
        raise NotImplementedError()
