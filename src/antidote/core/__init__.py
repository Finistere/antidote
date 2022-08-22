from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    cast,
    ContextManager,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    overload,
    Sequence,
    Type,
    TYPE_CHECKING,
    TypeVar,
    Union,
)

from typing_extensions import Concatenate, final, Literal, ParamSpec, Protocol, TypeAlias

from .._internal import API, Default
from .._internal.typing import F, T
from ._objects import app_catalog, inject, world
from .annotation import InjectMe
from .data import (
    CatalogId,
    DebugInfoPrefix,
    Dependency,
    DependencyDebug,
    dependencyOf,
    LifeTime,
    ParameterDependency,
    TestContextKind,
)
from .exceptions import (
    AntidoteError,
    CannotInferDependencyError,
    DependencyDefinitionError,
    DependencyNotFoundError,
    DoubleInjectionError,
    DuplicateDependencyError,
    DuplicateProviderError,
    FrozenCatalogError,
    MissingProviderError,
    UndefinedScopeVarError,
)
from .provider import ProvidedDependency, Provider, ProviderCatalog
from .scope import Missing, ScopeGlobalVar, ScopeVarToken
from .utils import is_catalog, is_compiled, is_readonly_catalog, new_catalog
from .wiring import Methods, wire, Wiring

if TYPE_CHECKING:
    from ..lib.interface_ext import instanceOf, PredicateConstraint

__all__ = [
    "AntidoteError",
    "CannotInferDependencyError",
    "Catalog",
    "CatalogId",
    "CatalogOverride",
    "DebugInfoPrefix",
    "Dependency",
    "DependencyDebug",
    "is_readonly_catalog",
    "DependencyDefinitionError",
    "DependencyNotFoundError",
    "DoubleInjectionError",
    "DuplicateDependencyError",
    "DuplicateProviderError",
    "FrozenCatalogError",
    "Inject",
    "InjectMe",
    "LifeTime",
    "LifetimeType",
    "Methods",
    "Missing",
    "MissingProviderError",
    "ParameterDependency",
    "ProvidedDependency",
    "Provider",
    "ProviderCatalog",
    "PublicCatalog",
    "ReadOnlyCatalog",
    "ScopeGlobalVar",
    "ScopeVarToken",
    "TestContextBuilder",
    "TestContextKind",
    "TypeHintsLocals",
    "UndefinedScopeVarError",
    "Wiring",
    "app_catalog",
    "dependencyOf",
    "inject",
    "is_catalog",
    "is_compiled",
    "new_catalog",
    "wire",
    "world",
]

U = TypeVar("U")
P = ParamSpec("P")
AnyProvider = TypeVar("AnyProvider", bound=Provider)
AnyNoArgsCallable = TypeVar("AnyNoArgsCallable", bound=Callable[[], object])

##########
# PUBLIC #
##########

LifetimeType: TypeAlias = Union[Literal["singleton", "scoped", "transient"], LifeTime]
TypeHintsLocals: TypeAlias = Union[Mapping[str, object], Literal["auto"], Default, None]


@API.private  # Protocol itself is private, methods are public
class DependencyAccessor(Protocol):
    @overload
    def get(
        self,
        __dependency: Dependency[T] | Type[instanceOf[T]],
    ) -> Optional[T]:
        ...

    @overload
    def get(
        self,
        __dependency: Type[T],
    ) -> Optional[T]:
        ...

    @overload
    def get(
        self,
        __dependency: object,
    ) -> Optional[object]:
        ...

    @overload
    def get(self, __dependency: Dependency[T] | Type[instanceOf[T]], default: U) -> T | U:
        ...

    @overload
    def get(self, __dependency: Type[T], default: U) -> T | U:
        ...

    @overload
    def get(self, __dependency: Callable[P, T], default: U) -> Callable[P, T] | U:
        ...

    @overload
    def get(self, __dependency: object, default: object) -> object:
        ...

    @API.public
    def get(
        self,
        __dependency: Any,
        default: object = None,
    ) -> object:
        """
        Return the value for the specified dependency if in the catalog, else *default*. If
        *default* is not given, it defaults to :py:obj:`None`, so that this method never raises a
        :py:exc:`.DependencyNotFoundError` (subclass of :py:exc:`KeyError`).

        :py:obj:`.inject` provides an equivalent API to specify a lazily injected dependency.

        .. doctest:: core_dependency_accessor_get

            >>> from antidote import world, const, inject
            >>> class Conf:
            ...     HOST = const('localhost')
            ...     UNKNOWN = 1
            >>> world.get(Conf.HOST)
            'localhost'
            >>> world.get(Conf.UNKNOWN) is None
            True
            >>> world.get(Conf.UNKNOWN, default='something')
            'something'
            >>> @inject
            ... def f(host: str = inject.get(Conf.HOST),
            ...       unknown: object = inject.get(Conf.UNKNOWN),
            ...       something: object = inject.get(Conf.UNKNOWN, default='something')) -> object:
            ...     return host, unknown, something
            >>> f()
            ('localhost', None, 'something')
        """
        ...

    # for @interface & @lazy & custom
    @overload
    def __getitem__(self, __dependency: Dependency[T] | Type[instanceOf[T]]) -> T:
        ...

    # for @injectable / @interface class
    @overload
    def __getitem__(self, __dependency: Type[T]) -> T:
        ...

    # for @interface function
    @overload
    def __getitem__(self, __dependency: Callable[P, T]) -> Callable[P, T]:
        ...

    @overload
    def __getitem__(self, __dependency: object) -> object:
        ...

    @API.public
    def __getitem__(self, __dependency: Any) -> object:
        """
        Return the value for the dependency. Raises a :py:exc:`.DependencyNotFoundError`
        (subclass of :py:exc:`KeyError`) if the dependency cannot be provided.

        :py:obj:`.inject` provides an equivalent API to specify a lazily injected dependency.

        .. doctest:: core_dependency_accessor_getitem

            >>> from antidote import world, const, inject
            >>> class Conf:
            ...     HOST = const('localhost')
            ...     UNKNOWN = 1
            >>> world[Conf.HOST]
            'localhost'
            >>> world.get(Conf.UNKNOWN) is None
            True
            >>> @inject
            ... def f(host: str = inject[Conf.HOST]) -> str:
            ...     return host
            >>> f()
            'localhost'
            >>> @inject
            ... def g(unknown: object = inject[Conf.UNKNOWN]) -> object:
            ...     return unknown
            >>> g()
            Traceback (most recent call last):
              File "<stdin>", line 1, in ?
            DependencyNotFoundError: ...
        """
        ...


@API.public
class ReadOnlyCatalog(DependencyAccessor, Protocol):
    @property
    def id(self) -> CatalogId:
        """
        Unique identifier of the Catalog. There's no backwards-compatibility guarantee on its value
        or type. It is only guaranteed to be unique.

        Its main purpose is to allow dependencies, such as :py:func:`.lazy` ones, to be aware of
        which catalog they've been registered.
        """
        ...

    def __contains__(self, __dependency: object) -> bool:
        """
        Returns :py:obj:`True` if the dependency can be provided, else :py:obj:`False`.
        """
        ...

    def debug(self, __obj: object, *, depth: int = -1) -> str:
        """
        If the object is a dependency that can be provided, a tree representation of all of its
        transitive dependencies, as the catalog would retrieve them, is returned. Otherwise, if the
        specified object is a callable with any injected dependencies, a tree representation of
        their debug output is returned.

        The tree is created idendepently from the values, so no singleton or bound
        dependencies will be instantiated.

        .. doctest:: readonly_catalog_debug

            >>> from antidote import world, const, injectable, inject
            >>> class Conf:
            ...     HOST = const('localhost')
            >>> @injectable
            ... class Dummy:
            ...     def __init__(self, host: str = inject[Conf.HOST]) -> None:
            ...         ...
            >>> print(world.debug(Dummy))
            🟉 Dummy
            └── Dummy.__init__
                └── 🟉 <const> 'localhost'
            <BLANKLINE>
            ∅ = transient
            ↻ = bound
            🟉 = singleton
            <BLANKLINE>

        Args:
            __obj: Root of the dependency tree.
            depth: Maximum depth of the result tree. Defaults to -1 which implies not limit.

        """
        ...

    @property
    def is_frozen(self) -> bool:
        """
        Returns :py:obj:`True` if the catalog is frozen, else :py:obj:`False`. A frozen catalog
        cannot be changed anymore, all new dependency registrations will fail.
        """
        ...

    def raise_if_frozen(self) -> None:
        """
        Raises an :py:exc:`.FrozenCatalogError` if the catalog is frozen. This is used to prevent
        any new registrations and have a more predictable catalog once frozen.
        """
        ...


_P = TypeVar("_P", bound="Provider")


# for a weird reason PyRight had issues detecting DependencyAccessor
@API.public
class Catalog(ReadOnlyCatalog, DependencyAccessor, Protocol):
    """
    Subclass of :py:class:`.ReadOnlyCatalog` for dependency access.

    A catalog is a collection of dependencies that can be provided. It ensures that singletons
    and bound dependencies are created in a thread-safe manner. But the actual instantiation
    is handled by one of its :py:class:`.Provider`.

    A catalog may have one or more child catalogs which are traversed after the providers. So any
    dependency defined in the catalog's children can be overridden by the catalog's own providers.
    To prevent any race conditions on the catalog locks, a catalog can only have one parent and as
    such be included only once.

    Catalogs are always created by pair, a private and a public (:py:class:`.PublicCatalog`) one.
    Most of the time one would manipulate the public one. The private's only purpose is to allow the
    definition of private dependencies which are not directly accessible from the public catalog.
    This is only needed for library/framework authors who want to expose only a subset of the
    dependencies registered. In this case, it's recommended to freeze the catalog before exposing
    it to ensure proper isolation.

    .. doctest:: core_catalog

        >>> from antidote import new_catalog, injectable, world
        >>> catalog = new_catalog(name='my-catalog')
        >>> @injectable(catalog=catalog)
        ... class Dummy:
        ...     pass
        >>> Dummy in world
        False
        >>> catalog[Dummy]
        <Dummy object at ...>
        >>> world.include(catalog)
        >>> world[Dummy] is catalog[Dummy]
        True

    """

    @property
    def private(self) -> Catalog:
        """
        Returns the associated private :py:class:`.Catalog`, or itself if it's already the
        private one.

        .. doctest:: core_catalog_private

            >>> from antidote import world, injectable, inject
            >>> @injectable(catalog=world.private)
            ... class Dummy:
            ...     pass
            >>> Dummy in world
            False
            >>> @injectable
            ... class SuperDummy:
            ...     def __init__(self, dummy: Dummy = inject.me()) -> None:
            ...         self.dummy = dummy
            >>> world[SuperDummy].dummy
            <Dummy object at ...>

        """
        ...

    @property
    def providers(self) -> CatalogProvidersMapping:
        """
        Returns a :py:class:`Mapping` of the providers type to their instance included in the
        catalog. It's only needed when creating a custom :py:class:`.Provider`.

        The returned mapping is immutable and changes to the catalog will *not* be reflected.

        .. warning::

            Beware, :py:class:`.Provider` are at the core of a :py:class:`.Catalog`. Be sure to
            understand all the implications of manipulating one. None of the Antidote provided
            :py:class:`.Provider` is part of the public API.

        """
        ...

    @overload
    def include(self, __obj: Type[_P]) -> Type[_P]:
        ...

    @overload
    def include(self, __obj: Callable[[Catalog], object] | PublicCatalog) -> None:
        ...

    def include(self, __obj: Any) -> Any:
        """
        Include something into the catalog. Multiple inputs are supported:

        - A :py:class:`.Provider` class will add a new provider to the :py:class:`.Catalog`. It
          behaves like a class decorator in this case.
        - A :py:class:`.PublicCatalog` which will be included as a child. Beware that a catalog can
          only have one parent. Private catalog cannot be added as a child.
        - A function accepting the current catalog as argument. It's typically used by an extension
          to initialize a catalog with child catalogs, providers or dependencies.

        .. doctest:: world_provider

            >>> from antidote import world, new_catalog, Catalog
            >>> my_catalog = new_catalog(name='custom')
            >>> world.include(my_catalog)
            >>> def my_extension(catalog: Catalog) -> None:
            ...     hidden_catalog = new_catalog(name='hidden')
            ...     catalog.include(hidden_catalog)
            >>> world.include(my_extension)
        """
        ...


@API.public
@final
@dataclass(frozen=True, eq=False)
class CatalogProvidersMapping(Mapping[Type[Provider], Provider]):
    """
    Immutable mapping of one catalog's providers. Beware, this is actually used as a Protocol
    despite
    """

    __slots__ = ("__wrapped",)
    __wrapped: Mapping[Type[Provider], Provider]

    def __repr__(self) -> str:
        return f"CatalogProviders({self.__wrapped!r})"

    def __len__(self) -> int:
        return len(self.__wrapped)

    def __getitem__(self, __provider_class: Type[AnyProvider]) -> AnyProvider:
        try:
            return cast(AnyProvider, self.__wrapped[__provider_class])
        except KeyError:
            raise MissingProviderError(__provider_class)

    def __contains__(self, __provider_class: object) -> bool:
        return __provider_class in self.__wrapped

    def __iter__(self) -> Iterator[Type[Provider]]:
        return iter(self.__wrapped)


@API.public
class PublicCatalog(Catalog, Protocol):
    """
    Subclass of :py:class:`.ReadOnlyCatalog` for dependency access and :py:class:`.Catalog` for
    dependency registration.

    Can be created with :py:func:`.new_catalog`.
    """

    @property
    def test(self) -> TestContextBuilder:
        """
        See :py:class:`.TestContextBuilder`.
        """
        ...

    def freeze(self) -> None:
        """
        Freezes the catalog, no additional dependencies, child catalog or providers can be added.
        Currently, it does not provide any performance improvements but may in the future.

        .. doctest:: world_freeze

            >>> from antidote import world, injectable
            >>> world.freeze()
            >>> @injectable
            ... class Dummy:
            ...     pass
            Traceback (most recent call last):
            ...
            FrozenCatalogError
            >>> world.is_frozen
            True

        """
        ...


@API.public
class TestContextBuilder(Protocol):
    """
    Used to create test environments with proper isolation and the possibility to create or
    override dependencies easily:

    .. doctest:: core_public_catalog_test

        >>> from antidote import world
        >>> with world.test.new() as overrides:
        ...     overrides['hello'] = 'world'
        ...     world['hello']
        'world'

    Within the context manager (:code:`with` block), :code:`world` will behave like a different
    Catalog and changes will not be propagated back. Four different test environment exist:

    - :py:meth:`~.TestCatalogBuilder.empty`: the catalog will be totally empty.
    - :py:meth:`~.TestCatalogBuilder.new`: the catalog will keep all of its
      :py:class:`.Provider` and child catalog. But those will be empty as if no dependency was
      ever registered.
    - :py:meth:`~.TestCatalogBuilder.clone`: All of the :py:class:`.Provider`, child catalog and
      dependency registration are kept. However, the catalog does not keep any of the dependency
      values (singletons, ...) as if it was never used. By default, the catalog will be frozen.
    - :py:meth:`~.TestCatalogBuilder.copy`: Same strategy than
      :py:meth:`~.TestCatalogBuilder.clone` except all existing dependencies are kept. Be
      careful with this test environment, dependencies values are not copied. The actual
      singletons values are exposed.

    It is also possible to nest the different test enviroments allowing to set up an environment
    and re-use it for different tests.

    .. doctest:: core_public_catalog_test

        >>> from antidote import world
        >>> with world.test.new() as overrides:
        ...     overrides['hello'] = 'world'
        ...     with world.test.copy() as nested_overrides:
        ...         print(world['hello'])
        ...         nested_overrides['hello'] = "new world"
        ...         print(world['hello'])
        ...     print(world['hello'])
        world
        new world
        world

    Each test environment exposes a :py:class:`.CatalogOverride` can create/override
    dependencies:

    .. doctest:: core_public_catalog_test

        >>> from antidote import world
        >>> with world.test.new() as overrides:
        ...     # create/override a singleton
        ...     overrides['hello'] = 'world'
        ...     # replace previous one
        ...     overrides['hello'] = 'new world'
        ...     # delete a dependency
        ...     del overrides['hello']
        ...     # create/override multiple dependencies at once
        ...     overrides.update({'my': 'world'})
        ...     # or use a factory which by default creates a non-singleton:
        ...     @overrides.factory('env')
        ...     def build() -> str:
        ...         return "test"

    When using a test environment on a catalog, it will also be applied on all children,
    recursively. It's also possible to override dependencies only within a specific catalog:

    .. doctest:: core_public_catalog_test

        >>> from antidote import world, new_catalog
        >>> catalog = new_catalog(name='child')
        >>> world.include(catalog)
        >>> with world.test.clone() as overrides:
        ...     # overrides.of(catalog) also supports del, update() and factory()
        ...     overrides.of(catalog)['hello'] = 'child'
        ...     print(catalog['hello'])
        ...     # It's also possible to modify the private catalog
        ...     overrides.of(world.private)['hello'] = 'private'
        ...     print(world.private['hello'])
        child
        private
        >>> 'hello' in catalog
        False

    """

    def copy(self, *, frozen: bool = True) -> ContextManager[CatalogOverrides]:
        """
        Creates a test enviroment keeping a copy of all child catalogs, :py:class:`.Provider`s,
        registered dependencies and even their values if any. Unscoped dependencies also keep their
        current values. If :py:func:`.UnscopedCallback.update` was called and the dependency value
        wasn't updated yet, the arguments passed to :py:func:`.UnscopedCallback.update` will also be
        kept. By default, the catalog will be frozen. However, child catalogs will keep their
        previous state, staying unfrozen if they weren't and frozen if not.

        .. warning::

            Be careful with this test environment, you'll be modifying existing dependency values!

        .. doctest:: core_test_copy

            >>> from antidote import injectable, world
            >>> @injectable
            ... class Service:
            ...     pass
            >>> with world.test.copy():
            ...     # Existing dependencies are kept
            ...     Service in world
            True
            >>> service = world[Service]
            >>> with world.test.copy():
            ...     # dependency values also are
            ...     world[Service] is service
            True
            >>> with world.test.copy():
            ...     # which implies that modification to singletons are propagated!
            ...     world[Service].hello = 'world'
            >>> world[Service].hello
            'world'
            >>> with world.test.copy() as overrides:
            ...     # overrides won't though
            ...     overrides[Service] = Service()
            ...     world[Service] is service
            False
            >>> world[Service] is service
            True
            >>> with world.test.copy():
            ...     # By default, world will be frozen
            ...     @injectable
            ...     class MyService:
            ...         pass
            Traceback (most recent call last):
            ...
            FrozenCatalogError
            >>> with world.test.copy(frozen=False):
            ...     # Now new dependencies can be declared
            ...     @injectable
            ...     class MyService:
            ...         pass
            ...     world[MyService]
            <MyService object at ...>
            >>> # They won't impact the real world though
            ... MyService in world
            False

        """
        ...

    def clone(self, *, frozen: bool = True) -> ContextManager[CatalogOverrides]:
        """
        Creates a test enviroment keeping a copy of all child catalogs, :py:class:`.Provider` and
        reigstered dependencies, state ones included. Existing dependency values are not copied.
        Unscoped dependencies will be reset to their initial value if any. By default, the catalog
        will be frozen. However, child catalogs will keep their previous state, staying unfrozen
        if they weren't and frozen if not.

        .. doctest:: core_test_clone

            >>> from antidote import injectable, world
            >>> @injectable
            ... class Service:
            ...     pass
            >>> with world.test.clone():
            ...     # Existing dependencies are kept
            ...     Service in world
            True
            >>> service = world[Service]
            >>> with world.test.clone():
            ...     # dependency values are not
            ...     world[Service] is service
            False
            >>> with world.test.clone():
            ...     # By default, world will be frozen
            ...     @injectable
            ...     class MyService:
            ...         pass
            Traceback (most recent call last):
            ...
            FrozenCatalogError
            >>> with world.test.clone(frozen=False):
            ...     # Now new dependencies can be declared
            ...     @injectable
            ...     class MyService:
            ...         pass
            ...     world[MyService]
            <MyService object at ...>
            >>> # They won't impact the real world though
            ... MyService in world
            False

        """
        ...

    def new(
        self,
        *,
        include: Iterable[Union[Callable[[Catalog], object], PublicCatalog, Type[Provider]]]
        | Default = Default.sentinel,
    ) -> ContextManager[CatalogOverrides]:
        """
        Creates a test environment with the beahvior as one created freshly with
        :py:func:`.new_catalog`. The :code:`include` argument behaves in the same way, an iterable
        of objects that will be included in the catalog with :py:meth:`.Catalog.include`.

        .. doctest:: world_test_new

            >>> from antidote import world, injectable
            >>> @injectable
            ... class Service:
            ...     pass
            >>> with world.test.new():
            ...     Service in world
            False
            >>> with world.test.new():
            ...     # Whether world was originally frozen or not, it won't be with new().
            ...     @injectable
            ...     class MyService:
            ...         pass
            ...     world[MyService]
            <MyService object at ...>
            >>> # They won't impact the real world though
            ... MyService in world
            False

        """
        ...

    def empty(self) -> ContextManager[CatalogOverrides]:
        """
        Creates an empty test environment. This is mostly useful when testing a
        :py:class:`.Provider`.

        .. doctest:: world_test_new

            >>> from antidote import world, injectable, antidote_lib_injectable
            >>> @injectable
            ... class Service:
            ...     pass
            >>> with world.test.empty():
            ...     Service in world
            False
            >>> with world.test.empty():
            ...     # Cannot use @injectable as no providers have been included.
            ...     @injectable
            ...     class MyService:
            ...         pass
            Traceback (most recent call last):
            ...
            MissingProviderError
            >>> with world.test.empty():
            ...     world.include(antidote_lib_injectable)
            ...     @injectable
            ...     class MyService:
            ...         pass
            ...     world[MyService]
            <MyService object at ...>

        """
        ...


@API.public
class CatalogOverride(Protocol):
    """
    See :py:meth:`.PublicCatalog.test` for its usage.
    """

    def __setitem__(self, __dependency: object, __value: object) -> None:
        """
        Set a dependency to a singleton value.

        .. doctest:: core_override_setitem

            >>> from antidote import world, injectable
            >>> @injectable
            ... class Service:
            ...     pass
            >>> with world.test.new() as overrides:
            ...     overrides['hello'] = 'world'
            ...     world['hello']
            'world'
            >>> with world.test.new() as overrides:
            ...     overrides[Service] = 'something'
            ...     world[Service]
            'something'

        """
        ...

    def __delitem__(self, __dependency: object) -> None:
        """
        Remove a dependency from the catalog

        .. doctest:: core_override_delitem

            >>> from antidote import world, injectable
            >>> @injectable
            ... class Service:
            ...     pass
            >>> with world.test.new() as overrides:
            ...     del overrides[Service]
            ...     Service in world
            False

        """
        ...

    @overload
    def update(self, _: Mapping[Any, object] | Iterable[tuple[object, object]]) -> None:
        ...

    @overload
    def update(self, **kwargs: object) -> None:
        ...

    def update(self, *args: object, **kwargs: object) -> None:
        """
        Update the catalog with the key/value pairs, overwriting existing dependencies.

        It accepts either another dictionary object or an iterable of key/value pairs (as tuples
        or other iterables of length two). If keyword arguments are specified, the dictionary is
        then updated with those key/value pairs.

        .. doctest:: core_override_update

            >>> from antidote import world, injectable
            >>> @injectable
            ... class Service:
            ...     pass
            >>> with world.test.new() as overrides:
            ...     overrides.update({Service: None})
            ...     assert world[Service] is None
            ...     overrides.update(hello='world')
            ...     assert world['hello'] == 'world'
            ...     overrides.update([(42, 420)])
            ...     assert world[42] == 420

        """
        ...

    def factory(
        self, __dependency: object, *, singleton: bool = False
    ) -> Callable[[AnyNoArgsCallable], AnyNoArgsCallable]:
        """
        Register a dependency with a factory function. By default, the lifetime of the dependency is
        :py:obj:`.None` meaning the factory is executed on each access. The dependency can
        also be declared as a singleton.

        .. doctest:: core_override_factory

            >>> from antidote import world, injectable
            >>> @injectable
            ... class Service:
            ...     pass
            >>> with world.test.new() as overrides:
            ...     @overrides.factory(Service)
            ...     def build() -> str:
            ...         return "dummy"
            ...     world[Service]
            'dummy'
            >>> with world.test.new() as overrides:
            ...     @overrides.factory('random')
            ...     def build() -> object:
            ...         return object()
            ...     world['random'] is world['random']
            False
            >>> with world.test.new() as overrides:
            ...     @overrides.factory('sentinel', singleton=True)
            ...     def build() -> object:
            ...         return object()
            ...     world['sentinel'] is world['sentinel']
            True

        """
        ...


@API.public
class CatalogOverrides(CatalogOverride, Protocol):
    """
    See :py:meth:`.PublicCatalog.test`.
    """

    def of(self, catalog: Catalog) -> CatalogOverride:
        """
        Return the associated overrides for the specified catalog. Raises a :py:exc:`KeyError` if
        the catalog is not overridable (not a child) in this test environment.

        .. doctest:: core_overrides_of

            >>> from antidote import world, new_catalog
            >>> catalog = new_catalog(name='child')
            >>> world.include(catalog)
            >>> with world.test.clone() as overrides:
            ...     # overrides.of(catalog) also supports del, update() and factory()
            ...     overrides.of(catalog)['hello'] = 'child'
            ...     print(catalog['hello'])
            ...     # It's also possible to modify the private catalog
            ...     overrides.of(world.private)['hello'] = 'private'
            ...     print(world.private['hello'])
            child
            private
            >>> 'hello' in catalog
            False

        """
        ...


@API.public
class Inject(DependencyAccessor, Protocol):
    """
    Use the singleton :py:obj:`.inject`.
    """

    @staticmethod
    def me(
        *constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object] | tuple[object, ...]] = None,
        qualified_by_one_of: Optional[list[object] | tuple[object, ...]] = None,
    ) -> Any:
        """
        Injection Marker specifying that the current type hint should be used as dependency.

        .. doctest:: core_inject_me

            >>> from antidote import inject, injectable
            >>> @injectable
            ... class MyService:
            ...     pass
            >>> @inject
            ... def f(s: MyService = inject.me()) -> MyService:
            ...     return s
            >>> f()
            <MyService object at ...>

        When the type hint is :code:`Optional` :py:func:`.inject` won't raise
        :py:exc:`~.exceptions.DependencyNotFoundError` but will provide :py:obj:`None` instead:

        .. doctest:: core_inject_me_optional

            >>> from typing import Optional
            >>> from antidote import inject
            >>> class MyService:
            ...     pass
            >>> @inject
            ... def f(s: Optional[MyService] = inject.me()) -> MyService:
            ...     return s
            >>> f() is None
            True

        :py:func:`.interface` are also supported:

        .. doctest:: core_inject_me_interface

            >>> from typing import Sequence
            >>> from antidote import inject, interface, implements
            >>> @interface
            ... class Alert:
            ...     pass
            >>> @implements(Alert)
            ... class DefaultAlert(Alert):
            ...     pass
            >>> @inject
            ... def get_single(alert: Alert = inject.me()) -> Alert:
            ...     return alert
            >>> get_single()
            <DefaultAlert object at ...>
            >>> @inject
            ... def get_all(alerts: Sequence[Alert] = inject.me()) -> Sequence[Alert]:
            ...     return alerts
            >>> get_all()
            [<DefaultAlert object at ...>]

        Args:
            *constraints: :py:class:`.PredicateConstraint` to evaluate for each implementation.
            qualified_by: All specified qualifiers must qualify the implementation.
            qualified_by_one_of: At least one of the specified qualifiers must qualify the
                implementation.
        """
        ...

    @API.experimental
    def rewire(
        self,
        __func: Callable[..., object] | staticmethod[Any] | classmethod[Any],
        *,
        app_catalog: ReadOnlyCatalog,
        method: bool | Default = Default.sentinel,
    ) -> None:
        """
        Rewire the function to use the specified catalog if the injection wasn't hardwired.

        .. doctest:: core_inject_rewire

            >>> from antidote import inject, app_catalog, new_catalog, world, injectable
            >>> @injectable
            ... class Service:
            ...     pass
            >>> @inject
            ... def f(x: Service = inject.me()) -> Service:
            ...     return x
            >>> @inject(app_catalog=world)
            ... def g(x: Service = inject.me()) -> Service:
            ...     return x
            >>> catalog = new_catalog()
            >>> # f() will now retrieve dependencies from `catalog`
            ... inject.rewire(f, app_catalog=catalog)
            >>> # f() will now retrieve dependencies from `app_catalog`, which was the default
            ... # behavior
            ... inject.rewire(f, app_catalog=app_catalog)
            >>> # has no impact as the catalog was explicitly hardwired
            ... inject.rewire(g, app_catalog=catalog)
        """
        ...

    @overload
    def __call__(
        self,
        *,
        args: Sequence[object] | None = ...,
        kwargs: Mapping[str, object] | None = ...,
        fallback: Mapping[str, object] | None = ...,
        ignore_type_hints: bool = ...,
        ignore_defaults: bool = ...,
        type_hints_locals: TypeHintsLocals = ...,
        app_catalog: API.Experimental[ReadOnlyCatalog | None] = ...,
    ) -> Callable[[F], F]:
        ...

    @overload
    def __call__(
        self,
        __arg: staticmethod[F],
        *,
        args: Sequence[object] | None = ...,
        kwargs: Mapping[str, object] | None = ...,
        fallback: Mapping[str, object] | None = ...,
        ignore_type_hints: bool = ...,
        ignore_defaults: bool = ...,
        type_hints_locals: TypeHintsLocals = ...,
        app_catalog: API.Experimental[ReadOnlyCatalog | None] = ...,
    ) -> staticmethod[F]:
        ...

    @overload
    def __call__(
        self,
        __arg: classmethod[F],
        *,
        args: Sequence[object] | None = ...,
        kwargs: Mapping[str, object] | None = ...,
        fallback: Mapping[str, object] | None = ...,
        ignore_type_hints: bool = ...,
        ignore_defaults: bool = ...,
        type_hints_locals: TypeHintsLocals = ...,
        app_catalog: API.Experimental[ReadOnlyCatalog | None] = ...,
    ) -> classmethod[F]:
        ...

    @overload
    def __call__(
        self,
        __arg: F,
        *,
        args: Sequence[object] | None = ...,
        kwargs: Mapping[str, object] | None = ...,
        fallback: Mapping[str, object] | None = ...,
        ignore_type_hints: bool = ...,
        ignore_defaults: bool = ...,
        type_hints_locals: TypeHintsLocals = ...,
        app_catalog: API.Experimental[ReadOnlyCatalog | None] = ...,
    ) -> F:
        ...

    def __call__(
        self,
        __arg: Any = None,
        *,
        args: Sequence[object] | None = None,
        kwargs: Mapping[str, object] | None = None,
        fallback: Mapping[str, object] | None = None,
        ignore_type_hints: bool = False,
        ignore_defaults: bool = False,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        app_catalog: API.Experimental[ReadOnlyCatalog | None] = None,
    ) -> Any:
        """
        Wrap a function to inject dependencies when executed. Dependencies can be tight to arguments
        in multiple ways. The priority is defined as follows:

        1. :code:`args` and :code:`kwargs`: argument name to dependencies.
        2. Defaults (ex: :py:meth:`~.Inject.me`) or PEP-593 Annotated type hints
           (ex: :py:obj:`.InjectMe`)
        3. :code:`fallback`: argument name to dependencies.

        .. doctest:: core_inject

            >>> from antidote import inject, injectable, InjectMe
            >>> @injectable
            ... class A:
            ...     pass
            >>> @injectable
            ... class B:
            ...     pass
            >>> @inject
            ... def f1(a: A = inject.me()):
            ...     return a
            >>> f1() is world[A]
            True
            >>> @inject
            ... def f2(a: InjectMe[A]):  # PEP-593 annotation
            ...     return a
            >>> f2() is world[A]
            True
            >>> @inject(kwargs=dict(a=A))
            ... def f3(a):
            ...     return a
            >>> f3() is world[A]
            True
            >>> @inject(fallback=dict(a=A))
            ... def f4(a):
            ...     return a
            >>> f4() is world[A]
            True

        The decorator can be applied on any kind of function:

        .. doctest:: core_inject

            >>> class Dummy:
            ...     @staticmethod
            ...     @inject
            ...     def static_method(a: A = inject.me()) -> object:
            ...         return a
            ...
            ...     @inject
            ...     @classmethod
            ...     def class_method(cls, a: A = inject.me()) -> object:
            ...         return a
            >>> Dummy.static_method() is world[A]
            True
            >>> Dummy.class_method() is world[A]
            True
            >>> @inject
            ... async def f(a: A = inject.me()) -> A:
            ...     return a

        .. note::

            To inject the first argument of a method, commonly :code:`self`, see
            :py:meth:`~.Inject.method`.

        Args:
            __arg: **/positional-only/** Callable to be wrapped, which may also be a static or
                class method. If used as a decorator, it can be a sequence of dependencies or a
                mapping of argument names to their respective dependencies. For the former,
                dependencies are associated with the arguments through their position :py:obj:`None`
                can be used as a placeholder to ignore certain arguments.
            kwargs: Mapping of argument names to dependencies. This has the highest priority.
            fallback: Mapping of argument names to dependencies. This has the lowest priority.
            ignore_type_hints: If :py:obj:`True`, neither type hints nor :code:`type_hints_locals`
                will not be used at all. Defaults to :py:obj:`False`.
            ignore_defaults: If :py:obj:`True`, default values such as :code:`inject.me()` are
                ignored. Defaults to :py:obj:`False`.
            type_hints_locals: Local variables to use for :py:func:`typing.get_type_hints`. They
                can be explicitly defined by passing a dictionary or automatically detected with
                :py:mod:`inspect` and frame manipulation by specifying :code:`'auto'`. Specifying
                :py:obj:`None` will deactivate the use of locals. When :code:`ignore_type_hints` is
                :py:obj:`True`, this features cannot be used. The default behavior depends on the
                :py:data:`.config` value of :py:attr:`~.Config.auto_detect_type_hints_locals`. If
                :py:obj:`True` the default value is equivalent to specifying :code:`'auto'`,
                otherwise to :py:obj:`None`.
            app_catalog: Defines the :py:obj:`.app_catalog` to be used by the current injection
                and nested ones. If unspecified, the catalog used depends on the context. Usually
                it will be :py:obj:`.app_catalog` defined by a upstream :py:obj:`.inject`. If never
                never specified, it's py:obj:`.world`. However, dependencies such as
                :py:func:`.injectable` use :py:meth:`.Inject.rewire` to force the use of the catalog
                in which the dependency is registered. If explicitely specified, it cannot be
                changed afterwards and can be either a :py:class:`.Catalog` or
                :py:obj:`.app_catalog`. The latter forcing the use of the current
                :py:obj:`.app_catalog` could otherwise be rewired by :py:func:`.injectable` and
                alike.

        """
        ...

    @overload
    def method(
        self,
        *,
        args: Sequence[object] | None = ...,
        kwargs: Mapping[str, object] | None = ...,
        fallback: Mapping[str, object] | None = ...,
        ignore_type_hints: bool = ...,
        ignore_defaults: bool = ...,
        type_hints_locals: TypeHintsLocals = ...,
        app_catalog: API.Experimental[ReadOnlyCatalog | None] = ...,
    ) -> Callable[[Callable[Concatenate[Any, P], T]], InjectedMethod[P, T]]:
        ...

    @overload
    def method(
        self,
        __arg: Callable[Concatenate[Any, P], T],
        *,
        args: Sequence[object] | None = ...,
        kwargs: Mapping[str, object] | None = ...,
        fallback: Mapping[str, object] | None = ...,
        ignore_type_hints: bool = ...,
        ignore_defaults: bool = ...,
        type_hints_locals: TypeHintsLocals = ...,
        app_catalog: API.Experimental[ReadOnlyCatalog | None] = ...,
    ) -> InjectedMethod[P, T]:
        ...

    def method(
        self,
        __arg: Any = None,
        *,
        args: Sequence[object] | None = None,
        kwargs: Mapping[str, object] | None = None,
        fallback: Mapping[str, object] | None = None,
        ignore_type_hints: bool = False,
        ignore_defaults: bool = False,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        app_catalog: API.Experimental[ReadOnlyCatalog | None] = None,
    ) -> Any:
        """
        Specialized version of :py:obj:`.inject` for methods to also inject the first argument,
        commonly named :code:`self`. More precisely, the dependency for :code:`self` is defined
        to be the class itself and so the dependency value associated with it will be injected when
        not provided. So when called through the class :code:`self` will be injected but not when
        called through an instance.

        .. doctest:: core_inject_method

            >>> from antidote import inject, injectable, world
            >>> @injectable
            ... class Dummy:
            ...     @inject.method
            ...     def get_self(self) -> 'Dummy':
            ...         return self
            >>> Dummy.get_self() is world[Dummy]
            True
            >>> dummy = Dummy()
            >>> dummy.get_self() is dummy
            True

        The class will not be defined as a dependency magically:

        .. doctest:: core_inject_method

            >>> class Unknown:
            ...     @inject.method
            ...     def get_self(self) -> 'Unknown':
            ...         return self
            >>> Unknown.get_self()
            Traceback (most recent call last):
              File "<stdin>", line 1, in ?
            DependencyNotFoundError: ...

        For information on all other features, see :py:obj:`.inject`.

        Args:
            __arg: **/positional-only/** Callable to be wrapped, which may also be a static or
                class method. If used as a decorator, it can be a sequence of dependencies or a
                mapping of argument names to their respective dependencies. For the former,
                dependencies are associated with the arguments through their position :py:obj:`None`
                can be used as a placeholder to ignore certain arguments.
            kwargs: Mapping of argument names to dependencies. This has the highest priority.
            fallback: Mapping of argument names to dependencies. This has the lowest priority.
            ignore_type_hints: If :py:obj:`True`, neither type hints nor :code:`type_hints_locals`
                will not be used at all. Defaults to :py:obj:`False`.
            ignore_defaults: If :py:obj:`True`, default values such as :code:`inject.me()` are
                ignored. Defaults to :py:obj:`False`.
            type_hints_locals: Local variables to use for :py:func:`typing.get_type_hints`. They
                can be explicitly defined by passing a dictionary or automatically detected with
                :py:mod:`inspect` and frame manipulation by specifying :code:`'auto'`. Specifying
                :py:obj:`None` will deactivate the use of locals. When :code:`ignore_type_hints` is
                :py:obj:`True`, this features cannot be used. The default behavior depends on the
                :py:data:`.config` value of :py:attr:`~.Config.auto_detect_type_hints_locals`. If
                :py:obj:`True` the default value is equivalent to specifying :code:`'auto'`,
                otherwise to :py:obj:`None`.
            app_catalog: Defines the :py:obj:`.app_catalog` to be used by the current injection
                and nested ones. If unspecified, the catalog used depends on the context. Usually
                it will be :py:obj:`.app_catalog` defined by a upstream :py:obj:`.inject`. If never
                never specified, it's py:obj:`.world`. However, dependencies such as
                :py:func:`.injectable` use :py:meth:`.Inject.rewire` to force the use of the catalog
                in which the dependency is registered. If explicitely specified, it cannot be
                changed afterwards and can be either a :py:class:`.Catalog` or
                :py:obj:`.app_catalog`. The latter forcing the use of the current
                :py:obj:`.app_catalog` could otherwise be rewired by :py:func:`.injectable` and
                alike.

        """
        ...


@API.public
class InjectedMethod(Protocol[P, T]):
    @property
    def __wrapped__(self) -> Callable[Concatenate[Any, P], T]:
        ...

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        ...

    def __set_name__(self, owner: type, name: str) -> None:
        ...

    @overload
    def __get__(self, instance: None, owner: type) -> InjectedMethod[P, T]:
        ...

    @overload
    def __get__(self, instance: object, owner: type) -> Callable[P, T]:
        ...

    def __get__(self, instance: object, owner: type) -> Any:
        ...
