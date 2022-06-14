from __future__ import annotations

from typing import Type, TYPE_CHECKING

from .._internal import API, debug_repr

if TYPE_CHECKING:
    from . import Provider, ReadOnlyCatalog
    from ._internal_catalog import InternalCatalog

__all__ = [
    "AntidoteError",
    "DependencyDefinitionError",
    "DependencyNotFoundError",
    "DuplicateDependencyError",
    "FrozenCatalogError",
    "DoubleInjectionError",
    "CannotInferDependencyError",
    "MissingProviderError",
    "UndefinedScopeVarError",
    "DuplicateProviderError",
]


@API.public
class AntidoteError(Exception):
    """Base class of all errors of antidote."""

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self})"


@API.public
class DoubleInjectionError(AntidoteError):
    """
    Raised when injecting a function/method that already has been injected.
    """

    @API.private
    def __init__(self, func: object) -> None:
        super().__init__(f"Object {func} has already been injected by Antidote.")


@API.public
class CannotInferDependencyError(AntidoteError):
    """
    Raised by :py:meth:`.Inject.me` when the dependency could not be inferred from the type hints.
    """


@API.public
class DuplicateDependencyError(AntidoteError):
    """
    Raised when a dependency can already be provided.
    """


@API.public
class DependencyDefinitionError(AntidoteError):
    """
    Raised when a dependency was not correctly defined by a :py:class:`.Provider`.
    """


@API.public
class DependencyNotFoundError(AntidoteError, KeyError):
    """
    Raised when the dependency could not be found in the catalog.
    """

    @API.private
    def __init__(self, dependency: object, *, catalog: ReadOnlyCatalog | InternalCatalog) -> None:
        super().__init__(f"{catalog} cannot provide {dependency!r}")


@API.public
class MissingProviderError(AntidoteError, KeyError):
    """
    Raised when the provider is not included in the catalog.
    """

    @API.private
    def __init__(self, provider: type) -> None:
        super().__init__(debug_repr(provider))


@API.public
class DuplicateProviderError(AntidoteError):
    """
    Raised when the provider was already included in the catalog
    """

    @API.private
    def __init__(self, *, catalog: InternalCatalog, provider_class: Type[Provider]) -> None:
        super().__init__(f"{catalog} already has the provider: {provider_class.__name__}")


@API.public
class FrozenCatalogError(AntidoteError):
    """
    Raised by methods that cannot be used with a frozen catalog.
    """

    @API.private
    def __init__(self, catalog: ReadOnlyCatalog | InternalCatalog) -> None:
        super().__init__(f"{catalog} is already frozen.")


@API.public
class UndefinedScopeVarError(AntidoteError, RuntimeError):
    """
    Raised when accessing the value of scope var for which it wasn't defined yet.
    """

    @API.private
    def __init__(self, dependency: object) -> None:
        super().__init__(
            f"ScopeVar {dependency!r} does not have any value associated."
            f"Use set() to define it first."
        )
