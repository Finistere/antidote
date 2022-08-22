from __future__ import annotations

from typing_extensions import Protocol

from ._internal import API, ConfigImpl
from .core import (
    AntidoteError,
    app_catalog,
    CannotInferDependencyError,
    Catalog,
    Dependency,
    DependencyNotFoundError,
    dependencyOf,
    DoubleInjectionError,
    DuplicateDependencyError,
    FrozenCatalogError,
    inject,
    InjectMe,
    is_catalog,
    is_compiled,
    is_readonly_catalog,
    LifeTime,
    LifetimeType,
    Methods,
    Missing,
    MissingProviderError,
    new_catalog,
    ParameterDependency,
    PublicCatalog,
    ReadOnlyCatalog,
    scope,
    ScopeGlobalVar,
    ScopeVarToken,
    TypeHintsLocals,
    UndefinedScopeVarError,
    wire,
    Wiring,
    world,
)
from .lib import antidote_lib
from .lib.injectable_ext import antidote_lib_injectable, injectable
from .lib.interface_ext import (
    AmbiguousImplementationChoiceError,
    antidote_lib_interface,
    HeterogeneousWeightError,
    ImplementationWeight,
    implements,
    instanceOf,
    interface,
    is_interface,
    MergeablePredicate,
    MergeablePredicateConstraint,
    NeutralWeight,
    Predicate,
    PredicateConstraint,
    QualifiedBy,
    SingleImplementationNotFoundError,
)
from .lib.lazy_ext import (
    antidote_lib_lazy,
    const,
    is_lazy,
    lazy,
    LazyFunction,
    LazyMethod,
    LazyProperty,
    LazyValue,
)

__all__ = [
    "AmbiguousImplementationChoiceError",
    "AntidoteError",
    "CannotInferDependencyError",
    "Catalog",
    "Dependency",
    "DependencyNotFoundError",
    "DoubleInjectionError",
    "DuplicateDependencyError",
    "FrozenCatalogError",
    "HeterogeneousWeightError",
    "ImplementationWeight",
    "InjectMe",
    "LazyFunction",
    "LazyMethod",
    "LazyProperty",
    "LazyValue",
    "LifeTime",
    "LifetimeType",
    "MergeablePredicate",
    "MergeablePredicateConstraint",
    "Methods",
    "Missing",
    "MissingProviderError",
    "NeutralWeight",
    "ParameterDependency",
    "Predicate",
    "PredicateConstraint",
    "PublicCatalog",
    "QualifiedBy",
    "ReadOnlyCatalog",
    "ScopeGlobalVar",
    "ScopeVarToken",
    "SingleImplementationNotFoundError",
    "TypeHintsLocals",
    "UndefinedScopeVarError",
    "Wiring",
    "__version__",
    "antidote_lib",
    "app_catalog",
    "config",
    "const",
    "dependencyOf",
    "antidote_lib_injectable",
    "antidote_lib_interface",
    "antidote_lib_lazy",
    "implements",
    "inject",
    "injectable",
    "instanceOf",
    "interface",
    "is_catalog",
    "is_compiled",
    "is_interface",
    "is_lazy",
    "is_readonly_catalog",
    "lazy",
    "new_catalog",
    "scope",
    "wire",
    "world",
]


try:
    from ._internal.scm_version import version as __version__
except ImportError:  # pragma: no cover
    __version__ = ""

world.include(antidote_lib)

config: Config = ConfigImpl()  # pyright: ignore


@API.public
class Config(Protocol):
    """
    This class itself shouldn't be used directly, rely on the singleton :py:obj:`.config` instead.

    Global configuration used by Antidote to (de-)activate features.
    """

    auto_detect_type_hints_locals: bool
    """
    Whether :py:obj:`.inject` and all other decorators should rely on inspection to determine
    automatically the locals for :py:func:`typing.get_type_hints` when relying on type hints.
    Deactivated by default. This behavior can always be overridden by specifying
    :code:`type_hints_locals` argument explicitly, either to :py:obj:`None` for deactivation or
    to :code:`'auto'` for activation.

    It's mostly interesting during tests. The following example wouldn't work with
    string annotations:

    .. doctest:: config_auto_detect_type_hints_locals

        >>> from __future__ import annotations
        >>> from antidote import config, injectable, inject, world
        >>> config.auto_detect_type_hints_locals = True
        >>> def dummy_test():
        ...     with world.test.new():
        ...         @injectable
        ...         class Dummy:
        ...             pass
        ...
        ...         @inject
        ...         def f(dummy: Dummy = inject.me()) -> Dummy:
        ...             return dummy
        ...
        ...         return f() is world.get(Dummy)
        >>> dummy_test()
        True

    .. testcleanup:: config_auto_detect_type_hints_locals

        config.auto_detect_type_hints_locals = False

    """
