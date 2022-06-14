from __future__ import annotations

import collections.abc as c_abc
import inspect
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    cast,
    Mapping,
    Optional,
    overload,
    Sequence,
    TYPE_CHECKING,
    TypeVar,
)

from typing_extensions import final, get_args, get_origin, Literal, TypeAlias

from .._internal import (
    API,
    Default,
    EMPTY_DICT,
    EMPTY_TUPLE,
    is_optional,
    optional_value,
    retrieve_or_validate_injection_locals,
    Singleton,
)
from ._annotation import is_valid_class_type_hint
from ._catalog import AppCatalog, CatalogImpl
from ._get import DependencyAccessorImpl
from ._injection import InjectionBlueprint, InjectionParameters
from ._internal_catalog import InternalCatalog
from ._wrapper import rewrap, wrap
from .data import Dependency, dependencyOf, ParameterDependency
from .exceptions import CannotInferDependencyError

if TYPE_CHECKING:
    from ..lib.interface import PredicateConstraint
    from . import ReadOnlyCatalog, TypeHintsLocals

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])
AnyF: TypeAlias = "Callable[..., Any] | staticmethod[Any] | classmethod[Any]"


@API.private  # Use the singleton instance `inject`, not the class directly.
@final
@dataclass(frozen=True, eq=False, init=False)
class InjectorImpl(DependencyAccessorImpl, Singleton):
    __slots__ = ("method",)
    method: Any

    def __init__(self) -> None:
        super().__init__(loader=lambda dependency: dependency)

        def method(*args: Any, **kwargs: Any) -> Any:
            kwargs["_inject_self"] = True
            kwargs["type_hints_locals"] = retrieve_or_validate_injection_locals(
                kwargs.get("type_hints_locals", Default.sentinel)
            )
            return self(*args, **kwargs)

        object.__setattr__(self, "method", method)

    @staticmethod
    def me(
        *constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object] | tuple[object, ...]] = None,
        qualified_by_one_of: Optional[list[object] | tuple[object, ...]] = None,
    ) -> Any:
        kwargs = dict(qualified_by=qualified_by, qualified_by_one_of=qualified_by_one_of)
        return InjectMeDependency(
            args=constraints, kwargs={k: v for k, v in kwargs.items() if v is not None}
        )

    def rewire(
        self,
        __func: F | staticmethod[F] | classmethod[F],
        *,
        catalog: InternalCatalog | ReadOnlyCatalog,
        method: bool | Default = Default.sentinel,
    ) -> None:
        internal: InternalCatalog | None = None
        if isinstance(catalog, CatalogImpl):
            internal = catalog.internal
        elif isinstance(catalog, InternalCatalog):
            internal = catalog
        elif not isinstance(catalog, AppCatalog):
            raise TypeError(f"catalog must be a Catalog or None, not a {type(catalog)!r}")

        if isinstance(__func, (classmethod, staticmethod)):
            rewrap(__func.__func__, catalog=internal, inject_self=method)
        elif inspect.isfunction(__func):
            rewrap(__func, catalog=internal, inject_self=method)
        else:
            raise TypeError(f"Expected a function or class/static-method, not a {type(__func)!r}")

    @overload
    def __call__(
        self,
        *,
        catalog: InternalCatalog | ReadOnlyCatalog | None = ...,
        kwargs: Mapping[str, object] | None = ...,
        fallback: Mapping[str, object] | None = ...,
        ignore_type_hints: bool = ...,
        ignore_defaults: bool = ...,
        type_hints_locals: TypeHintsLocals = ...,
    ) -> Callable[[F], F]:
        ...

    @overload
    def __call__(
        self,
        __arg: staticmethod[F],
        *,
        catalog: InternalCatalog | ReadOnlyCatalog | None = ...,
        kwargs: Mapping[str, object] | None = None,
        fallback: Mapping[str, object] | None = ...,
        ignore_type_hints: bool = ...,
        ignore_defaults: bool = ...,
        type_hints_locals: TypeHintsLocals = ...,
    ) -> staticmethod[F]:
        ...

    @overload
    def __call__(
        self,
        __arg: classmethod[F],
        *,
        catalog: InternalCatalog | ReadOnlyCatalog | None = ...,
        kwargs: Mapping[str, object] | None = ...,
        fallback: Mapping[str, object] | None = ...,
        ignore_type_hints: bool = ...,
        ignore_defaults: bool = ...,
        type_hints_locals: TypeHintsLocals = ...,
    ) -> classmethod[F]:
        ...

    @overload
    def __call__(
        self,
        __arg: F,
        *,
        catalog: InternalCatalog | ReadOnlyCatalog | None = ...,
        kwargs: Mapping[str, object] | None = ...,
        fallback: Mapping[str, object] | None = ...,
        ignore_type_hints: bool = ...,
        ignore_defaults: bool = ...,
        type_hints_locals: TypeHintsLocals = ...,
    ) -> F:
        ...

    @overload
    def __call__(
        self,
        __arg: Sequence[object | None],
        *,
        catalog: InternalCatalog | ReadOnlyCatalog | None = ...,
        fallback: Mapping[str, object] | None = ...,
        ignore_type_hints: bool = ...,
        ignore_defaults: bool = ...,
        type_hints_locals: TypeHintsLocals = ...,
    ) -> Callable[[F], F]:
        ...

    @overload
    def __call__(
        self,
        __arg: Mapping[str, object],
        *,
        catalog: InternalCatalog | ReadOnlyCatalog | None = ...,
        fallback: Mapping[str, object] | None = ...,
        ignore_type_hints: bool = ...,
        ignore_defaults: bool = ...,
        type_hints_locals: TypeHintsLocals = ...,
    ) -> Callable[[F], F]:
        ...

    def __call__(
        self,
        __arg: Any = None,
        *,
        catalog: InternalCatalog | ReadOnlyCatalog | None = None,
        kwargs: Mapping[str, object] | None = None,
        fallback: Mapping[str, object] | None = None,
        ignore_type_hints: bool = False,
        ignore_defaults: bool = False,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        _inject_self: bool = False,
    ) -> Any:
        if not isinstance(ignore_type_hints, bool):
            raise TypeError(f"ignore_type_hints must be a boolean, not {type(ignore_type_hints)!r}")
        if not isinstance(ignore_defaults, bool):
            raise TypeError(f"ignore_defaults must be a boolean, not {type(ignore_defaults)!r}")
        if not (
            fallback is None
            or (
                isinstance(fallback, c_abc.Mapping)
                and all(isinstance(key, str) for key in fallback.keys())
            )
        ):
            raise TypeError(
                f"fallback must be a mapping of of argument names to dependencies or None, "
                f"not {type(fallback)!r}"
            )
        if not (
            kwargs is None
            or (
                isinstance(kwargs, c_abc.Mapping)
                and all(isinstance(key, str) for key in kwargs.keys())
            )
        ):
            raise TypeError(
                f"kwargs must be a mapping of of argument names to dependencies or None, "
                f"not {type(kwargs)!r}"
            )
        args: Sequence[object | None] | None = None
        if isinstance(__arg, (c_abc.Sequence, c_abc.Mapping)):
            if isinstance(__arg, str):
                raise TypeError(
                    "First argument must be an sequence/mapping of dependencies "
                    "or the function to be wrapped, not a string."
                )
            if kwargs is not None:
                raise TypeError(
                    "Cannot specify argument dependencies as first argument AND kwargs "
                    "at the same time."
                )
            if isinstance(__arg, c_abc.Mapping):
                kwargs = __arg
            else:
                args = __arg
            __arg = None
        if ignore_type_hints:
            tp_locals: Optional[Mapping[str, object]] = None
        else:
            tp_locals = retrieve_or_validate_injection_locals(type_hints_locals)

        if catalog is not None:
            hardwired: bool = True
            if isinstance(catalog, CatalogImpl):
                maybe_internal_catalog: InternalCatalog | None = catalog.internal
            elif isinstance(catalog, InternalCatalog):
                maybe_internal_catalog = catalog
            elif isinstance(catalog, AppCatalog):
                maybe_internal_catalog = None
            else:
                raise TypeError(
                    f"catalog must be a ReadOnlyCatalog if specified, " f"not a {type(catalog)!r}"
                )
        else:
            hardwired = False
            maybe_internal_catalog = None

        def decorate(obj: AnyF) -> AnyF:
            nonlocal kwargs

            if inspect.isclass(obj):
                # User-friendlier error for classes.
                raise TypeError("Classes cannot be wrapped with @inject. Consider using @wire")

            parameters = InjectionParameters.of(
                obj,
                ignore_type_hints=ignore_type_hints,
                type_hints_locals=tp_locals,
            )

            if _inject_self and (
                not parameters.has_self
                or not len(parameters)
                or isinstance(obj, (staticmethod, classmethod))
            ):
                raise TypeError(
                    "Can only use @inject.method on methods, not static/class ones or functions."
                )

            if args is not None:
                if len(args) > len(parameters.without_self):
                    raise ValueError(
                        f"More dependencies ({args}) were provided than function "
                        f"arguments ({len(parameters)})"
                    )

                assert kwargs is None
                kwargs = {}
                for arg, parameter in zip(args, parameters.without_self):
                    if arg is not None:
                        kwargs[parameter.name] = arg

            if kwargs and not set(kwargs.keys()).issubset(set(parameters.names())):
                unexpected = set(kwargs.keys()).difference(parameters.names())
                raise ValueError(
                    f"Unexpected dependencies for " f"missing arguments: {', '.join(unexpected)}"
                )

            blueprint = InjectionBlueprint.create(
                parameters=parameters,
                fallback=fallback or {},
                kwargs=kwargs or {},
                ignore_defaults=ignore_defaults,
                inject_self=_inject_self,
            )
            # If nothing can be injected, just return the existing function without
            # any overhead.
            if blueprint.is_empty():
                return obj

            wrapper = wrap(
                obj.__func__ if isinstance(obj, (classmethod, staticmethod)) else obj,
                blueprint=blueprint,
                catalog=maybe_internal_catalog,
                hardwired=hardwired,
            )

            if isinstance(obj, staticmethod):
                return staticmethod(wrapper)
            elif isinstance(obj, classmethod):
                return classmethod(wrapper)
            return wrapper

        return __arg and decorate(__arg) or decorate


@API.private  # See @inject decorator for usage.
@final
@dataclass(frozen=True, eq=True, unsafe_hash=True)
class InjectMeDependency(ParameterDependency):
    __slots__ = ("args", "kwargs")
    args: tuple[Any, ...]
    kwargs: dict[str, Any]

    def __init__(self, *, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        object.__setattr__(self, "args", args or EMPTY_TUPLE)
        object.__setattr__(self, "kwargs", kwargs or EMPTY_DICT)

    def __antidote_parameter_dependency__(
        self, *, name: str, type_hint: object, type_hint_with_extras: object
    ) -> Dependency[object]:
        from collections.abc import Iterable, Sequence

        from ..lib.interface import instanceOf

        original_type_hint = type_hint
        optional = False
        while is_optional(type_hint):
            type_hint = optional_value(type_hint)
            optional = True
        origin = get_origin(type_hint)
        args = get_args(type_hint)

        if origin in {Sequence, Iterable, list}:
            klass = args[0]
            method: Literal["all"] | Literal["single"] = "all"
        else:
            klass = type_hint
            method = "single"

        # Support generic interfaces
        klass = get_origin(klass) or klass
        if not is_valid_class_type_hint(klass):
            raise CannotInferDependencyError(
                f"Cannot use inject.me with builtins, found: {original_type_hint!r}"
            )

        if method == "single" and not self.args and not self.kwargs:
            dep = klass
        else:
            dep = cast(Any, getattr(instanceOf[Any](klass), method))(*self.args, **self.kwargs)
        return dependencyOf[object](dep, default=None if optional else Default.sentinel)
