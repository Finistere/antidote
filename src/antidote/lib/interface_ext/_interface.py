from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    cast,
    Generic,
    Mapping,
    Optional,
    overload,
    Sequence,
    Type,
    TYPE_CHECKING,
    TypeVar,
)

from typing_extensions import final, get_args, get_origin, ParamSpec

from ..._internal import (
    API,
    Default,
    enforce_subclass_if_possible,
    prepare_injection,
    retrieve_or_validate_injection_locals,
    Singleton,
)
from ..._internal.typing import C, T
from ...core import Catalog, is_catalog, LifeTime, TypeHintsLocals, Wiring, world
from ..injectable_ext import injectable
from ..lazy_ext import const, is_lazy, lazy, LazyFunction, LazyMethod
from ._function import FunctionInterfaceImpl, LazyInterfaceImpl
from ._internal import create_conditions, ImplementationsRegistryDependency
from .predicate import ImplementationWeight, MergeablePredicate, NeutralWeight, Predicate

if TYPE_CHECKING:
    from . import (
        FunctionInterface,
        InterfaceDecorator,
        InterfaceLazyAsDefaultDecorator,
        InterfaceLazyDecorator,
        LazyInterface,
    )

__all__ = [
    "InterfaceImpl",
    "ImplementsImpl",
    "register_overridable_class",
]

P = ParamSpec("P")
Pred = TypeVar("Pred", bound=Predicate[Any])
Weight = TypeVar("Weight", bound=ImplementationWeight)


@API.private
@final
@dataclass(frozen=True)
class Prepared(Generic[T]):
    __slots__ = ("out", "dependency")
    out: T
    dependency: T


@API.private
@final
@dataclass(frozen=True, eq=False)
class InterfaceImpl(Singleton):
    __slots__ = ("lazy",)
    lazy: InterfaceLazyImpl

    def __init__(self) -> None:
        lazy = InterfaceLazyImpl(self)
        object.__setattr__(self, "lazy", lazy)

    @overload
    def __call__(self, __obj: C, *, catalog: Catalog = ...) -> C:
        ...

    @overload
    def __call__(
        self,
        __obj: Callable[P, T],
        *,
        catalog: Catalog = ...,
    ) -> FunctionInterface[P, T]:
        ...

    @overload
    def __call__(self, *, catalog: Catalog = ...) -> InterfaceDecorator:
        ...

    def __call__(
        self, __obj: object = None, *, catalog: Catalog = world, _lazy: bool = False
    ) -> object:
        if not is_catalog(catalog):
            raise TypeError(f"catalog must be a Catalog, not a {type(catalog)!r}")

        def register(obj: Any) -> Any:
            from ._provider import InterfaceProvider

            provider = catalog.providers[InterfaceProvider]
            if isinstance(obj, type):
                provider.register(obj)
                return obj
            elif inspect.isfunction(obj):
                provider.register(obj)
                if _lazy:
                    return LazyInterfaceImpl(wrapped=obj, catalog=catalog)
                return FunctionInterfaceImpl(wrapped=obj, catalog=catalog)
            else:
                raise TypeError(f"Expected a class or a function, not a {type(obj)!r}")

        return __obj and register(__obj) or register

    @overload
    def as_default(
        self,
        __obj: C,
        *,
        wiring: Wiring | None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> C:
        ...

    @overload
    def as_default(
        self,
        __obj: Callable[P, T],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> FunctionInterface[P, T]:
        ...

    @overload
    def as_default(
        self,
        *,
        inject: None = ...,
        wiring: Wiring | None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> InterfaceDecorator:
        ...

    def as_default(
        self,
        __obj: object = None,
        *,
        inject: None | Default = Default.sentinel,
        wiring: Wiring | None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog = world,
        _lazy: bool = False,
    ) -> object:
        if not is_catalog(catalog):
            raise TypeError(f"catalog must be a Catalog, not a {type(catalog)!r}")

        def register(
            obj: Any,
            type_hints_locals: Mapping[str, object]
            | None = retrieve_or_validate_injection_locals(type_hints_locals),
        ) -> Any:
            from . import implements, interface

            if isinstance(obj, type):
                assert inject is Default.sentinel, "inject is not a valid parameter for a class"
                register_overridable_class(
                    interface=obj,
                    type_hints_locals=type_hints_locals,
                    catalog=catalog,
                    wiring=wiring,
                )
                return obj
            elif _lazy and (inspect.isfunction(obj) or is_lazy(obj)):
                assert wiring is Default.sentinel, "wiring is not a valid parameter for a function"
                lazy_interface = interface.lazy(catalog=catalog)(
                    cast(Any, obj).__wrapped__ if is_lazy(obj) else obj
                )
                impl = implements.lazy(
                    lazy_interface, inject=inject, type_hints_locals=type_hints_locals
                ).as_default(obj)
                object.__setattr__(lazy_interface, "__wrapped__", impl.__wrapped__)
                return lazy_interface
            elif inspect.isfunction(obj):
                assert wiring is Default.sentinel, "wiring is not a valid parameter for a function"
                func_interface = interface(catalog=catalog)(obj)
                impl = implements(
                    func_interface, inject=inject, type_hints_locals=type_hints_locals
                ).as_default(obj)
                object.__setattr__(
                    func_interface, "__wrapped__", getattr(impl, "__wrapped__", impl)
                )
                return func_interface
            elif is_lazy(obj):
                raise TypeError("Use @overridable.lazy with a lazy function.")
            else:
                raise TypeError(f"Expected a class or a function, not a {type(obj)!r}")

        return __obj and register(__obj) or register


@API.private
@final
@dataclass(frozen=True, eq=False)
class InterfaceLazyImpl(Singleton):
    __slots__ = ("__interface",)
    __interface: InterfaceImpl

    @overload
    def __call__(self, *, catalog: Catalog = ...) -> InterfaceLazyDecorator:
        ...

    @overload
    def __call__(
        self,
        __func: LazyFunction[P, T],
        *,
        catalog: Catalog = ...,
    ) -> LazyInterface[P, T]:
        ...

    @overload
    def __call__(
        self,
        __func: Callable[P, T],
        *,
        catalog: Catalog = ...,
    ) -> LazyInterface[P, T]:
        ...

    def __call__(
        self,
        __func: object = None,
        *,
        catalog: Catalog = world,
    ) -> object:
        return self.__interface(__func, catalog=catalog, _lazy=True)  # type: ignore

    @overload
    def as_default(
        self,
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = world,
    ) -> InterfaceLazyAsDefaultDecorator:
        ...

    @overload
    def as_default(
        self,
        __func: staticmethod[LazyFunction[P, T]],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = world,
    ) -> LazyInterface[P, T]:
        ...

    @overload
    def as_default(
        self,
        __func: LazyMethod[P, T],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = world,
    ) -> LazyInterface[P, T]:
        ...

    @overload
    def as_default(
        self,
        __func: LazyFunction[P, T],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = world,
    ) -> LazyInterface[P, T]:
        ...

    @overload
    def as_default(
        self,
        __func: Callable[P, T],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = world,
    ) -> LazyInterface[P, T]:
        ...

    def as_default(
        self,
        __func: object = None,
        *,
        inject: None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog = world,
    ) -> object:
        return self.__interface.as_default(  # type: ignore
            __func,
            catalog=catalog,
            inject=inject,
            type_hints_locals=retrieve_or_validate_injection_locals(type_hints_locals),
            _lazy=True,
        )


@API.private
@final
@dataclass(eq=False)
class ImplementsImpl(Generic[T]):
    __slots__ = ("__explicit_interface", "__type_hint_locals", "__catalog", "__prepare", "__dict__")
    __explicit_interface: T
    __catalog: Catalog
    __prepare: Callable[[T], Prepared[T]]

    @property
    def __interface(self) -> T:
        if self.__explicit_interface is not None:
            return self.__explicit_interface
        cls = get_args(cast(Any, self).__orig_class__)[0]
        return cast(T, get_origin(cls) or cls)

    def __init__(
        self,
        *,
        interface: T | None = None,
        wiring: Wiring | None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog | Default = Default.sentinel,
        inject: None | Default = Default.sentinel,
        _lazy: bool = False,
    ) -> None:
        from ._function import LazyInterfaceImpl

        if not (isinstance(catalog, Default) or is_catalog(catalog)):
            raise TypeError(f"catalog must be a Catalog, not a {type(catalog)!r}")

        valid_locals = retrieve_or_validate_injection_locals(type_hints_locals)

        if (
            interface is None
            or isinstance(interface, type)
            or isinstance(get_origin(interface), type)
        ):
            if _lazy:
                raise TypeError(
                    "Cannot use @implements.lazy with classes, " "use @implements instead."
                )
            assert inject is Default.sentinel, "inject is not a valid parameter for a class"
            interface = cast(T, get_origin(interface) or interface)
            valid_catalog: Catalog = world if isinstance(catalog, Default) else catalog

            def prepare(obj: Any) -> Prepared[Any]:
                if not isinstance(obj, type):
                    raise TypeError(f"Expected a class for the implementation, got a {type(obj)!r}")
                enforce_subclass_if_possible(obj, self.__interface)  # type: ignore
                if obj not in valid_catalog.private:
                    injectable(
                        obj,
                        type_hints_locals=valid_locals,
                        catalog=valid_catalog.private,
                        wiring=wiring if not isinstance(wiring, Default) else Wiring(),
                    )
                elif not isinstance(wiring, Default):
                    raise RuntimeError(
                        f"Class already exists in the catalog {valid_catalog.private}, and thus "
                        f"@implements refuses to apply the specified wiring as one was probably "
                        f"already applied."
                    )
                return Prepared(obj, obj)

        elif isinstance(interface, LazyInterfaceImpl):
            if not _lazy:
                raise TypeError(
                    "Cannot use @implements with lazy functions, use @implements.lazy instead."
                )
            assert wiring is Default.sentinel, "wiring is not a valid parameter for a function"
            assert catalog is Default.sentinel, "catalog is not a valid parameter for a function"
            valid_catalog = interface.catalog
            interface = cast(T, interface.wrapped)
            signature = inspect.signature(cast(Any, interface))

            def prepare(obj: Any) -> Prepared[Any]:
                if not (is_lazy(obj) or inspect.isfunction(obj)):
                    raise TypeError(
                        f"Expected a lazy function for the implementation, got a {type(obj)!r}"
                    )
                ensure_signature_matches(obj, expected=signature)
                if not is_lazy(obj):
                    obj = lazy(
                        obj,
                        type_hints_locals=valid_locals,
                        catalog=valid_catalog.private,
                        inject=inject,
                    )

                return Prepared(out=obj, dependency=const(obj, catalog=valid_catalog.private))

        elif isinstance(interface, FunctionInterfaceImpl):
            if _lazy:
                raise TypeError(
                    "Cannot use @implements.lazy with a standard function, "
                    "use @implements instead."
                )
            assert wiring is Default.sentinel, "wiring is not a valid parameter for a function"
            assert catalog is Default.sentinel, "catalog is not a valid parameter for a function"
            valid_catalog = interface.catalog
            interface = cast(T, interface.wrapped)
            signature = inspect.signature(cast(Any, interface))

            inject_ = prepare_injection(
                inject=inject,
                catalog=valid_catalog.private,
                type_hints_locals=retrieve_or_validate_injection_locals(type_hints_locals),
            )

            def prepare(obj: Any) -> Prepared[Any]:
                if is_lazy(obj):
                    raise TypeError(
                        "Cannot use a lazy function for a function interface. Either define "
                        "a lazy interface or use a standard function."
                    )
                if not inspect.isfunction(obj):
                    raise TypeError(
                        f"Expected a function for the implementation, got a {type(obj)!r}"
                    )
                ensure_signature_matches(obj, expected=signature)
                obj = inject_(obj)

                return Prepared(out=obj, dependency=const(obj, catalog=valid_catalog.private))

        else:
            raise TypeError(f"Expected an registered interface, not a {type(interface)!r}")

        object.__setattr__(self, f"_{type(self).__name__}__explicit_interface", interface)
        object.__setattr__(self, f"_{type(self).__name__}__catalog", valid_catalog)
        object.__setattr__(self, f"_{type(self).__name__}__prepare", prepare)

    def __call__(self, __impl: T) -> T:
        prepared = self.__prepare(__impl)
        self.__register_implementation(
            implementation=prepared,
            conditions=[],
        )
        return prepared.out

    def when(
        self,
        *_predicates: Predicate[Weight] | Predicate[NeutralWeight],
        qualified_by: Optional[object | list[object]] = None,
    ) -> Callable[[T], T]:
        def register(__impl: T) -> T:
            prepared = self.__prepare(__impl)
            self.__register_implementation(
                implementation=prepared,
                conditions=create_conditions(*_predicates, qualified_by=qualified_by),
            )
            return prepared.out

        return register

    def overriding(self, __existing_implementation: T) -> Callable[[T], T]:
        if isinstance(self.__interface, type) and not isinstance(__existing_implementation, type):
            raise TypeError(
                f"Expected a class for the overridden implementation, "
                f"got a {type(__existing_implementation)!r}"
            )
        elif (inspect.isfunction(self.__interface) or is_lazy(self.__interface)) and not (
            inspect.isfunction(__existing_implementation) or is_lazy(__existing_implementation)
        ):
            raise TypeError(
                f"Expected a function for the overridden implementation, "
                f"got a {type(__existing_implementation)!r}"
            )

        def register(__impl: T) -> T:
            prepared = self.__prepare(__impl)
            replaced = self.__catalog[ImplementationsRegistryDependency(self.__interface)].replace(
                current_identifier=__existing_implementation,
                new_identifier=prepared.out,
                new_dependency=prepared.dependency,
            )
            if not replaced:
                raise ValueError(
                    f"Implementation {__existing_implementation!r} " f"does not exist."
                )
            return prepared.out

        return register

    def as_default(self, __impl: T) -> T:
        prepared = self.__prepare(__impl)
        self.__catalog[ImplementationsRegistryDependency(self.__interface)].set_default(
            identifier=prepared.out, dependency=prepared.dependency
        )
        return prepared.out

    def __register_implementation(
        self,
        *,
        implementation: Prepared[T],
        conditions: Sequence[
            Predicate[Weight] | Predicate[NeutralWeight] | Weight | NeutralWeight | None | bool
        ],
    ) -> None:
        # Remove duplicates and combine predicates when possible
        weights: list[Weight] = list()
        distinct_predicates: dict[Type[Predicate[Any]], Predicate[Any]] = dict()
        for condition in conditions:
            if condition is None or condition is False:
                return
            if condition is True:
                continue
            if isinstance(condition, Predicate):
                cls = type(condition)
                previous = distinct_predicates.get(cls)
                if previous is not None:
                    if not issubclass(cls, MergeablePredicate):
                        raise TypeError(
                            f"Cannot have multiple predicates of type {cls!r} "
                            f"without declaring a merge method! See MergeablePredicate."
                        )
                    cls = cast(Type[MergeablePredicate[Any]], cls)  # type: ignore
                    distinct_predicates[cls] = cls.merge(
                        cast(MergeablePredicate[Any], previous),
                        cast(MergeablePredicate[Any], condition),
                    )
                else:
                    distinct_predicates[cls] = condition
            elif isinstance(condition, ImplementationWeight):
                if not isinstance(condition, NeutralWeight):
                    weights.append(condition)
            else:
                raise TypeError(
                    f"A condition must either be a predicate, an optional weight "
                    f"or a boolean, not a {type(condition)!r}"
                )

        self.__catalog[ImplementationsRegistryDependency(self.__interface)].add(
            identifier=implementation.out,
            dependency=implementation.dependency,
            predicates=list(distinct_predicates.values()),
            weights=weights,
        )


@API.private
def ensure_signature_matches(__func: Callable[..., object], *, expected: inspect.Signature) -> None:
    impl = inspect.signature(__func)
    missing = set(expected.parameters.keys()).difference(set(impl.parameters.keys()))
    if missing:
        raise TypeError(f"Missing arguments: {missing!r}")
    param: inspect.Parameter
    impl_param: inspect.Parameter
    for pos, ((name, param), (impl_name, impl_param)) in enumerate(
        zip(expected.parameters.items(), impl.parameters.items())
    ):
        if param.kind is param.POSITIONAL_OR_KEYWORD or param.kind is param.POSITIONAL_ONLY:
            if name != impl_name:
                raise TypeError(
                    f"Expected argument of name {name!r} at position {pos + 1}, found {impl_name!r}."
                )
        else:
            break

    for name, param in expected.parameters.items():
        impl_param = impl.parameters[name]
        if param.default is not param.empty and impl_param.default is param.empty:
            raise TypeError(f"Expected a default value for argument {name!r}, but none present.")


@API.private
def register_overridable_class(
    *,
    interface: type,
    type_hints_locals: Optional[Mapping[str, object]],
    catalog: Catalog,
    wiring: Wiring | None | Default,
) -> None:
    # TODO: need better logic, this is a hack to access any original @injectable
    # applied on the @overridable to keep whatever the user specified. Even
    # the ``register_injectable` use with `dependency` is poorly written.
    from ..injectable_ext._provider import FactoryProvider

    lifetime_factory = catalog.providers[FactoryProvider].pop(interface)
    if lifetime_factory is not None:
        if not isinstance(wiring, Default):
            raise RuntimeError(
                f"Class has already exists in the catalog {catalog.private}, and thus "
                f"@overridable refuses to apply the specified wiring as one was probably "
                f"already applied."
            )
        lifetime, factory = lifetime_factory
        dependency: object = lazy.value(
            factory, lifetime=lifetime, catalog=catalog.private, inject=None
        )
    else:
        if wiring is not None:
            (wiring if not isinstance(wiring, Default) else Wiring()).wire(
                klass=interface, type_hints_locals=type_hints_locals, app_catalog=catalog.private
            )

        dependency = lazy.value(
            interface, lifetime=LifeTime.SINGLETON, catalog=catalog.private, inject=None
        )

    from ._provider import InterfaceProvider

    catalog.providers[InterfaceProvider].register(interface).set_default(
        identifier=interface, dependency=dependency
    )
