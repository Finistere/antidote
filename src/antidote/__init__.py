from __future__ import annotations

from typing_extensions import Protocol

from ._internal import API, ConfigImpl
from .core import (
    app_catalog,
    Catalog,
    Dependency,
    DependencyNotFoundError,
    dependencyOf,
    DuplicateDependencyError,
    Inject,
    inject,
    is_catalog,
    is_compiled,
    LifeTime,
    Methods,
    new_catalog,
    PublicCatalog,
    scope,
    ScopeVar,
    ScopeVarToken,
    wire,
    Wiring,
    world,
)
from .lib import antidote_lib
from .lib.injectable import antidote_injectable, injectable
from .lib.interface import (
    antidote_interface,
    implements,
    instanceOf,
    interface,
    is_interface,
    overridable,
    Predicate,
    QualifiedBy,
)
from .lib.lazy import antidote_lazy, const, is_const_factory, is_lazy, lazy

__all__ = [
    "Inject",
    "dependencyOf",
    "instanceOf",
    "Predicate",
    "QualifiedBy",
    "Methods",
    "Wiring",
    "DependencyNotFoundError",
    "DuplicateDependencyError",
    "__version__",
    "const",
    "config",
    "LifeTime",
    "Catalog",
    "PublicCatalog",
    "implements",
    "inject",
    "antidote_lib",
    "injectable",
    "interface",
    "is_compiled",
    "lazy",
    "wire",
    "overridable",
    "world",
    "new_catalog",
    "antidote_interface",
    "antidote_injectable",
    "antidote_lazy",
    "app_catalog",
    "Dependency",
    "scope",
    "ScopeVar",
    "is_catalog",
    "is_lazy",
    "is_const_factory",
    "is_interface",
    "ScopeVarToken",
]

try:
    from ._internal.scm_version import version as __version__
except ImportError:  # pragma: no cover
    __version__ = ""

world.include(antidote_lib)

config: Config = ConfigImpl()
config.__doc__ = """
Singleton instance of :py:class:`.Config`.
"""


@API.public
class Config(Protocol):
    """
    This class itself shouldn't be used directly, rely on the singleton :py:obj:`.config` instead.

    Global configuration used by Antidote to (de-)activate features.
    """

    auto_detect_type_hints_locals: bool
    """
    Whether :py:func:`.inject`, :py:func:`.injectable`, :py:class:`.implements` and
    :py:func:`.wire` should rely on inspection to determine automatically the locals
    for :py:func:`typing.get_type_hints` when relying on type hints. Deactivated by default.
    This behavior can always be overridden by specifying :code:`type_hints_locals` argument
    explicitly, either to :py:obj:`None` for deactivation or to :code:`'auto'` for activation.

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
