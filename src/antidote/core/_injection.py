from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable, cast, Iterator, Mapping, Sequence, TYPE_CHECKING

from typing_extensions import Annotated, final, get_origin, get_type_hints, TypeGuard

from .._internal import API, is_optional, optional_value
from ._raw import is_wrapper, NotFoundSentinel, unwrap
from .data import Dependency, dependencyOf, ParameterDependency
from .exceptions import CannotInferDependencyError, DoubleInjectionError

if TYPE_CHECKING:
    pass

__all__ = [
    "InjectionParameter",
    "InjectionParameters",
    "InjectionBlueprint",
    "Injection",
    "create_blueprint",
]


@API.private
@final
@dataclass(frozen=True)
class Injection:
    """
    Maps an argument name to its dependency and if the injection is required,
    which is equivalent to no default argument.
    """

    __slots__ = ("arg_name", "required", "dependency", "default")
    arg_name: str
    dependency: object
    default: object


@API.private
@final
@dataclass(frozen=True)
class InjectionBlueprint:
    """
    Stores all the injections for a function.
    """

    __slots__ = ("injections", "positional_arguments_count", "inject_self")
    injections: tuple[Injection, ...]
    positional_arguments_count: int
    inject_self: bool


def create_blueprint(
    parameters: InjectionParameters,
    kwargs: Mapping[str, object],
    fallback: Mapping[str, object],
    ignore_defaults: bool,
    inject_self: bool,
) -> InjectionBlueprint | None:
    injections: list[Injection] = []
    for parameter in parameters:
        has_dependency_as_default = not ignore_defaults and _is_dependency(parameter.default)
        dep = None
        if parameter.name in kwargs:
            dep = kwargs[parameter.name]

        if dep is None:
            type_hint_with_extras = parameter.type_hint_with_extras
            while is_optional(type_hint_with_extras):
                type_hint_with_extras = optional_value(type_hint_with_extras)

            origin = get_origin(type_hint_with_extras)
            if origin is Annotated:
                __metadata: list[object] = type_hint_with_extras.__metadata__  # pyright: ignore
                dependencies: list[object] = [
                    extra for extra in __metadata if _is_dependency(extra)
                ]
                if len(dependencies) > 1:
                    raise CannotInferDependencyError(
                        f"Multiple Antidote dependencies annotations are not supported. "
                        f"Found {dependencies}"
                    )
                elif dependencies:
                    if has_dependency_as_default:
                        raise CannotInferDependencyError(
                            "Cannot specify both a default dependency "
                            "AND a annotated dependency."
                        )
                    dep = dependencies[0]

        if dep is None and has_dependency_as_default:
            dep = parameter.default

        if dep is None and parameter.name in fallback:
            dep = fallback[parameter.name]

        if isinstance(dep, ParameterDependency):
            _dependency = dependencyOf[object](
                dep.__antidote_parameter_dependency__(
                    name=parameter.name,
                    type_hint=parameter.type_hint,
                    type_hint_with_extras=parameter.type_hint_with_extras,
                )
            )
        else:
            _dependency = dependencyOf[object](dep)

        default = _dependency.default
        if default is NotFoundSentinel and not has_dependency_as_default and parameter.has_default:
            default = parameter.default

        injections.append(
            Injection(
                arg_name=parameter.name,
                dependency=_dependency.wrapped,
                default=default,
            )
        )

    if not inject_self and all(injection.dependency is None for injection in injections):
        return None

    return InjectionBlueprint(
        injections=tuple(injections),
        positional_arguments_count=parameters.positional_arguments_count,
        inject_self=inject_self,
    )


@API.private
def _is_dependency(x: object) -> TypeGuard[Dependency[object] | ParameterDependency]:
    return isinstance(x, (Dependency, ParameterDependency))


@API.private
@final
@dataclass(frozen=True)
class InjectionParameter:
    __slots__ = ("name", "default", "type_hint", "type_hint_with_extras", "to_ignore")
    name: str
    default: object
    type_hint: Any
    type_hint_with_extras: Any
    to_ignore: bool

    @property
    def has_default(self) -> bool:
        return self.default is not inspect.Parameter.empty


KW_ONLY_PARAMETERS = [
    inspect.Parameter.VAR_POSITIONAL,
    inspect.Parameter.VAR_KEYWORD,
    inspect.Parameter.KEYWORD_ONLY,
]
KW_PARAMETERS = [
    inspect.Parameter.POSITIONAL_OR_KEYWORD,
    inspect.Parameter.KEYWORD_ONLY,
]


@API.private
@final
@dataclass(frozen=True)
class InjectionParameters:
    """Used when generating the injection wrapper"""

    __slots__ = (
        "positional_arguments_count",
        "_parameters",
        "has_self",
    )
    positional_arguments_count: int
    _parameters: Sequence[InjectionParameter]
    has_self: bool

    @property
    def without_self(self) -> InjectionParameters:
        if not self.has_self:
            return self

        return InjectionParameters(
            positional_arguments_count=self.positional_arguments_count - 1,
            parameters=self._parameters[1:],
            has_self=False,
        )

    @classmethod
    def of(
        cls,
        __obj: object,
        *,
        ignore_type_hints: bool,
        type_hints_locals: Mapping[str, object] | None = None,
    ) -> tuple[inspect.Signature, InjectionParameters]:
        func = cast(
            Callable[..., Any],
            __obj.__func__ if isinstance(__obj, (staticmethod, classmethod)) else __obj,
        )
        func = inspect.unwrap(func, stop=is_wrapper)
        __unwrapped__ = unwrap(func)
        if __unwrapped__ is not None:
            raise DoubleInjectionError(__unwrapped__[0])

        if not inspect.isfunction(func):
            raise TypeError(f"Object {func} is neither a function nor a (class/static) method")

        if ignore_type_hints or (
            len(func.__annotations__) <= 1
            and (not func.__annotations__ or next(iter(func.__annotations__.keys())) == "return")
        ):
            type_hints = {}
            extra_type_hints = {}
        else:
            localns = dict(type_hints_locals) if type_hints_locals is not None else None
            type_hints = get_type_hints(func, localns=localns)
            extra_type_hints = get_type_hints(func, localns=localns, include_extras=True)

        positional_arguments_count = 0
        kw_only_arguments = False
        parameters: list[InjectionParameter] = []
        signature = inspect.signature(func, follow_wrapped=False)
        for name, parameter in signature.parameters.items():
            if parameter.kind in KW_ONLY_PARAMETERS:
                kw_only_arguments = True

            if not kw_only_arguments:
                positional_arguments_count += 1

            if parameter.kind in KW_PARAMETERS:
                parameters.append(
                    InjectionParameter(
                        name=name,
                        default=parameter.default,
                        type_hint=type_hints.get(name),
                        type_hint_with_extras=extra_type_hints.get(name),
                        to_ignore=False,
                    )
                )
            elif not kw_only_arguments:
                parameters.append(
                    InjectionParameter(
                        name=name,
                        default=parameter.default,
                        type_hint=None,
                        type_hint_with_extras=None,
                        to_ignore=True,
                    )
                )

        return signature, InjectionParameters(
            positional_arguments_count=positional_arguments_count,
            parameters=tuple(parameters),
            has_self=is_unbound_method(cast(Any, __obj)),
        )

    def __init__(
        self,
        *,
        positional_arguments_count: int,
        parameters: Sequence[InjectionParameter],
        has_self: bool,
    ) -> None:
        object.__setattr__(self, "positional_arguments_count", positional_arguments_count)
        object.__setattr__(self, "_parameters", parameters)
        object.__setattr__(self, "has_self", has_self)

    def __len__(self) -> int:
        return len(self._parameters)

    def __iter__(self) -> Iterator[InjectionParameter]:
        return iter(self._parameters)


@API.private
def is_unbound_method(func: Callable[..., object] | staticmethod[Any] | classmethod[Any]) -> bool:
    """
    # Methods and nested function will have a different __qualname__ than
    # __name__ (See PEP-3155).
    #
    # >>> class A:
    # ...     def f(self):
    # ...         pass
    # >>> A.f.__qualname__
    # 'A.f'
    #
    # This helps us differentiate method defined in a module and those for a class.
    """
    if isinstance(func, staticmethod):
        return False

    if isinstance(func, classmethod):
        return True

    return (
        func.__qualname__ != func.__name__  # not top level
        # not a bound method (self/cls already bound)
        and not inspect.ismethod(func)
        # not nested function
        and not func.__qualname__[: -len(func.__name__)].endswith("<locals>.")
    )
