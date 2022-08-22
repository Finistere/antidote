from __future__ import annotations

import builtins
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

from typing_extensions import final, get_args, get_origin, Literal, TypeAlias, TypeGuard

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
from ._catalog import AppCatalogProxy, CatalogImpl, CatalogOnion
from ._injection import create_blueprint, InjectionParameters
from ._raw import rewrap, wrap
from .data import Dependency, dependencyOf, ParameterDependency
from .exceptions import CannotInferDependencyError

if TYPE_CHECKING:
    from ..lib.interface_ext import PredicateConstraint
    from . import ReadOnlyCatalog, TypeHintsLocals

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])
AnyF: TypeAlias = "Callable[..., Any] | staticmethod[Any] | classmethod[Any]"

_BUILTINS_TYPES = {e for e in builtins.__dict__.values() if isinstance(e, type)}


@API.private
def is_valid_class_type_hint(type_hint: object) -> TypeGuard[type]:
    return (
        type_hint not in _BUILTINS_TYPES
        and isinstance(type_hint, type)
        and getattr(type_hint, "__module__", "") != "typing"
    )


@API.private  # Use the singleton instance `inject`, not the class directly.
@final
@dataclass(frozen=True, eq=False, init=False)
class InjectImpl(Singleton):
    __slots__ = ("method",)
    method: Any

    def __init__(self) -> None:
        def method(*args: Any, **kwargs: Any) -> Any:
            kwargs["_inject_self"] = True
            kwargs["type_hints_locals"] = retrieve_or_validate_injection_locals(
                kwargs.get("type_hints_locals", Default.sentinel)
            )
            return self(*args, **kwargs)

        object.__setattr__(self, "method", method)

    def get(self, __dependency: Any, default: Any = None) -> Any:
        return dependencyOf[Any](__dependency, default=default)

    def __getitem__(self, __dependency: Any) -> Any:
        return dependencyOf[Any](__dependency)

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
        app_catalog: ReadOnlyCatalog,
        method: bool | Default = Default.sentinel,
    ) -> None:
        maybe_app_catalog_onion: CatalogOnion | None = None
        if isinstance(app_catalog, CatalogImpl):
            maybe_app_catalog_onion = app_catalog.onion
        elif isinstance(app_catalog, AppCatalogProxy):
            maybe_app_catalog_onion = None
        else:
            raise TypeError(f"catalog must be a Catalog or None, not a {type(app_catalog)!r}")

        if isinstance(__func, (classmethod, staticmethod)):
            rewrap(
                __func.__func__, maybe_app_catalog_onion=maybe_app_catalog_onion, inject_self=method
            )
        elif inspect.isfunction(__func):
            rewrap(__func, maybe_app_catalog_onion=maybe_app_catalog_onion, inject_self=method)
        else:
            raise TypeError(f"Expected a function or class/static-method, not a {type(__func)!r}")

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
        app_catalog: ReadOnlyCatalog | None = ...,
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
        app_catalog: ReadOnlyCatalog | None = ...,
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
        app_catalog: ReadOnlyCatalog | None = ...,
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
        app_catalog: ReadOnlyCatalog | None = ...,
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
        app_catalog: ReadOnlyCatalog | None = None,
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
        if not (args is None or (isinstance(args, c_abc.Sequence) and not isinstance(args, str))):
            raise TypeError(f"args must be a sequence of dependencies, not {type(args)!r}")

        if ignore_type_hints:
            tp_locals: Optional[Mapping[str, object]] = None
        else:
            tp_locals = retrieve_or_validate_injection_locals(type_hints_locals)

        if app_catalog is not None:
            hardwired: bool = True
            if isinstance(app_catalog, CatalogImpl):
                maybe_app_catalog_onion: CatalogOnion | None = app_catalog.onion
            elif isinstance(app_catalog, AppCatalogProxy):
                maybe_app_catalog_onion = None
            else:
                raise TypeError(
                    f"app_catalog must be a ReadOnlyCatalog or app_catalog if specified, "
                    f"not a {type(app_catalog)!r}"
                )
        else:
            hardwired = False
            maybe_app_catalog_onion = None

        def decorate(
            obj: AnyF,
            kwargs: dict[str, object] | None = dict(kwargs) if kwargs is not None else None,
        ) -> AnyF:
            if inspect.isclass(obj):
                # User-friendlier error for classes.
                raise TypeError("Classes cannot be wrapped with @inject. Consider using @wire")

            signature, parameters = InjectionParameters.of(
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

            if args is not None or kwargs is not None:
                if args is not None and parameters.has_self:
                    signature = signature.replace(
                        parameters=list(signature.parameters.values())[1:]
                    )

                # Shouldn't fail
                signature.bind_partial(*(args or EMPTY_TUPLE), **(kwargs or EMPTY_DICT))
                if args is not None:
                    kwargs = kwargs or {}
                    for arg, parameter in zip(args, parameters.without_self):
                        if arg is not None:
                            kwargs[parameter.name] = arg

            maybe_blueprint = create_blueprint(
                parameters=parameters,
                fallback=fallback or {},
                kwargs=kwargs or {},
                ignore_defaults=ignore_defaults,
                inject_self=_inject_self,
            )
            # If nothing can be injected, just return the existing function without
            # any overhead.
            if maybe_blueprint is None:
                return obj

            wrapper = wrap(
                obj.__func__ if isinstance(obj, (classmethod, staticmethod)) else obj,
                blueprint=maybe_blueprint,
                maybe_app_catalog_onion=maybe_app_catalog_onion,
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
@dataclass(frozen=True, eq=True)
class InjectMeDependency(ParameterDependency):
    __slots__ = ("args", "kwargs")
    args: tuple[Any, ...] | None
    kwargs: dict[str, Any] | None

    def __init__(self, *, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        object.__setattr__(self, "args", args or EMPTY_TUPLE)
        object.__setattr__(self, "kwargs", kwargs or EMPTY_DICT)

    def __hash__(self) -> int:
        return hash((self.args, self.kwargs or None))

    def __antidote_parameter_dependency__(
        self, *, name: str, type_hint: object, type_hint_with_extras: object
    ) -> Dependency[object]:
        from collections.abc import Iterable, Sequence

        from ..lib.interface_ext import instanceOf

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
