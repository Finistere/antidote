from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, overload, Type, TYPE_CHECKING, TypeVar

from typing_extensions import Protocol

from .._internal import API, debug_repr
from .data import DependencyDebug, LifeTime

if TYPE_CHECKING:
    from . import ReadOnlyCatalog

__all__ = ["Provider", "ProvidedDependency"]

P = TypeVar("P", bound="Provider")
Result = TypeVar("Result")


# TODO: overload per enum value?
@API.public
class ProvidedDependency(Protocol):
    """
    Using by a :py:class:`.Provider` to return the value of a dependency.
    :py:meth:`.ProvidedDependency.set_value` can only be called once and will raise an error after.
    """

    @overload
    def set_value(
        self, value: Result, *, lifetime: LifeTime | None, callback: Callable[[], Result]
    ) -> None:
        ...

    @overload
    def set_value(self, value: object, *, lifetime: LifeTime | None) -> None:
        ...

    def set_value(
        self,
        value: Result,
        *,
        lifetime: LifeTime | None,
        callback: Callable[..., Result] | None = None,
    ) -> None:
        """
        Defines the value and the lifetime of a dependency. If a callback function is provided it
        will be used to generate the dependency value next time it's needed for the :code:`call`
        and :code:`bound` scopes instead traversing the whole catalog again. For the
        :code:`singleton` lifetime it's silently ignored.
        """
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
        >>> @dataclass
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
        ...             out.set_value(dependency.number ** 2, lifetime='transient')
        >>> world[SquareOf(12)]
        144

    Other than those two methods, the catalog will also call the following which have a default
    implementation:

    - :py:meth:`~.Provider.create` used when including the :py:class:`.Provider` in a catalog.
    - :py:meth:`~.Provider.copy` used for the :py:meth:`~.TestCatalogBuilder.copy` and
      :py:meth:`~.TestCatalogBuilder.clone` test environments.
    - :py:meth:`~.Provider.maybe_debug` use for :py:meth:`.Catalog.debug`.

    """

    __slots__ = ("_catalog",)
    _catalog: ReadOnlyCatalog

    @classmethod
    def create(cls: Type[P], catalog: ReadOnlyCatalog) -> P:
        """
        Used by the catalog to create an instance when using :py:meth:`.Catalog.include`.
        """
        return cls(catalog=catalog)

    def __init__(self, *, catalog: ReadOnlyCatalog) -> None:
        """
        The catalog only relies on :py:meth:`~.Provider.create` and :py:meth:`~.Provider.copy` for
        instantiation, so feel free to change :code:`__init__()` however you wish.
        """
        object.__setattr__(self, "_catalog", catalog)

    def unsafe_copy(self: P) -> P:
        """
        Used for the :py:meth:`~.TestCatalogBuilder.copy` and :py:meth:`~.TestCatalogBuilder.clone`
        test environments. It should return a deep copy of the provider, changes in the copy should
        not affect the original one.
        """
        return self.create(catalog=self._catalog)

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
                description=f"No debug provided by {debug_repr(type(self))}", lifetime="transient"
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
