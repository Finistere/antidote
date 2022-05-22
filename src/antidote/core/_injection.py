from __future__ import annotations

import collections.abc as c_abc
import inspect
from dataclasses import dataclass
from typing import (  # noqa: F401
    Any,
    Callable,
    cast,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Set,
    TYPE_CHECKING,
)

from typing_extensions import final, TypeAlias

from .exceptions import DoubleInjectionError, NoInjectionsFoundError
from .marker import Marker
from .._internal import API
from .._internal.argspec import Arguments
from .._internal.utils import Default
from .._internal.wrapper import (
    build_wrapper,
    get_wrapped,
    Injection,
    InjectionBlueprint,
    is_wrapper,
)

if TYPE_CHECKING:
    from .injection import DEPENDENCIES_TYPE, AUTO_PROVIDE_TYPE

AnyF: TypeAlias = "Callable[..., Any] | staticmethod[Any] | classmethod[Any]"


@API.private
@final
@dataclass(frozen=True, init=False)
class ArgDependency:
    __slots__ = ("dependency", "default")
    dependency: object
    default: object

    @classmethod
    def of(cls, x: object) -> ArgDependency:
        from .annotations import Get

        if isinstance(x, ArgDependency):
            return x
        if isinstance(x, Get):
            return ArgDependency(dependency=x.dependency, default=x.default)

        return ArgDependency(x)

    def __init__(self, dependency: object, *, default: object = Default.sentinel) -> None:
        object.__setattr__(self, "dependency", dependency)
        object.__setattr__(self, "default", default)


@API.private
def raw_inject(
    obj: AnyF,
    *,
    dependencies: DEPENDENCIES_TYPE,
    auto_provide: AUTO_PROVIDE_TYPE,
    strict_validation: bool,
    ignore_type_hints: bool,
    type_hints_locals: Optional[Mapping[str, object]],
) -> AnyF:
    if not isinstance(ignore_type_hints, bool):
        raise TypeError(f"ignore_type_hints must be a boolean, not {type(ignore_type_hints)}")

    if not isinstance(strict_validation, bool):
        raise TypeError(f"strict_validation must be a boolean, not {type(strict_validation)}")
    if inspect.isclass(obj):
        # User-friendlier error for classes.
        raise TypeError("Classes cannot be wrapped with @inject. objectConsider using @wire")
    if is_wrapper(obj):
        raise DoubleInjectionError(get_wrapped(obj))

    func = obj.__func__ if isinstance(obj, (classmethod, staticmethod)) else obj
    if not inspect.isfunction(func):
        raise TypeError(f"wrapped object {func} is neither a function nor a (class/static) method")

    unwrapped_func = inspect.unwrap(func, stop=lambda f: is_wrapper(f))
    if is_wrapper(unwrapped_func):
        raise DoubleInjectionError(get_wrapped(unwrapped_func))

    blueprint = _build_injection_blueprint(
        arguments=Arguments.from_callable(
            obj, ignore_type_hints=ignore_type_hints, type_hints_locals=type_hints_locals
        ),
        dependencies=dependencies,
        auto_provide=auto_provide,
        strict_validation=strict_validation,
    )
    # If nothing can be injected, just return the existing function without
    # any overhead.
    if blueprint.is_empty():
        if ignore_type_hints:
            raise NoInjectionsFoundError(
                f"No dependencies found while ignoring type hints for {obj}"
            )
        return obj

    wrapped_func = build_wrapper(blueprint=blueprint, wrapped=func)
    if isinstance(obj, staticmethod):
        return staticmethod(wrapped_func)
    if isinstance(obj, classmethod):
        return classmethod(wrapped_func)
    return cast(AnyF, wrapped_func)


@API.private
def _build_injection_blueprint(
    arguments: Arguments,
    dependencies: DEPENDENCIES_TYPE,
    auto_provide: AUTO_PROVIDE_TYPE,
    strict_validation: bool,
) -> InjectionBlueprint:
    """
    Construct a InjectionBlueprint with all the necessary information about
    the arguments for dependency injection. Storing it avoids significant
    execution overhead./

    Used by inject()
    """
    annotated = _build_from_annotations(arguments)
    explicit_dependencies = _build_from_dependencies(arguments, dependencies, strict_validation)
    auto_provided = _build_auto_provide(arguments, auto_provide, annotated, strict_validation)
    resolved_dependencies: List[ArgDependency] = [
        ArgDependency.of(
            annotated.get(
                arg.name, explicit_dependencies.get(arg.name, auto_provided.get(arg.name))
            )
        )
        for arg in arguments
    ]

    return InjectionBlueprint(
        tuple(
            Injection(
                arg_name=arg.name,
                required=isinstance(arg.default, Marker) or not arg.has_default,
                dependency=arg_dependency.dependency,
                default=arg_dependency.default,
            )
            for arg, arg_dependency in zip(arguments, resolved_dependencies)
        )
    )


@API.private
def _build_from_annotations(arguments: Arguments) -> Dict[str, object]:
    from ._annotations import extract_annotated_arg_dependency

    arg_to_dependency: Dict[str, object] = {}
    for arg in arguments:
        dependency = extract_annotated_arg_dependency(arg)
        if dependency is not None:
            arg_to_dependency[arg.name] = dependency

    return arg_to_dependency


@API.private
def _build_from_dependencies(
    arguments: Arguments, dependencies: DEPENDENCIES_TYPE, strict_validation: bool
) -> Dict[str, object]:
    from .injection import Arg

    if dependencies is None:
        arg_to_dependency: Mapping[str, object] = {}
    elif callable(dependencies):
        arg_to_dependency = {
            arg.name: dependencies(Arg(arg.name, arg.type_hint, arg.type_hint_with_extras))
            for arg in arguments.without_self
        }
    elif isinstance(dependencies, c_abc.Mapping):
        _check_valid_arg_names("dependencies", dependencies.keys(), arguments, strict_validation)
        arg_to_dependency = dependencies
    elif isinstance(dependencies, c_abc.Iterable) and not isinstance(dependencies, str):
        # convert to Tuple in case we cannot iterate more than once.
        dependencies = tuple(dependencies)
        if strict_validation and len(arguments.without_self) < len(dependencies):
            raise ValueError(
                f"More dependencies ({dependencies}) were provided than arguments ({arguments})"
            )
        arg_to_dependency = {
            arg.name: dependency for arg, dependency in zip(arguments.without_self, dependencies)
        }
    else:
        raise TypeError(
            f"Only a mapping or a iterable is supported for "
            f"dependencies, not {type(dependencies)!r}"
        )

    # Remove any None as they would hide type_hints.
    return {k: v for k, v in arg_to_dependency.items() if v is not None}


@API.private
def _build_auto_provide(
    arguments: Arguments,
    auto_provide: AUTO_PROVIDE_TYPE,
    annotated: Dict[str, object],
    strict_validation: bool,
) -> Dict[str, object]:
    from ._annotations import extract_auto_provided_arg_dependency

    auto_provide_set: Set[type] = set()
    if isinstance(auto_provide, bool):
        auto_provide_bool = auto_provide

        def is_auto_provided(__cls: type) -> bool:
            return auto_provide_bool

    elif isinstance(auto_provide, c_abc.Iterable):
        # convert to set in case we cannot iterate more than once.
        auto_provide_set = set(auto_provide)
        for cls in auto_provide_set:
            if not isinstance(cls, type):
                raise TypeError(
                    f"auto_provide must be a boolean or an iterable of "
                    f"classes, but contains {cls!r} which is not a class."
                )

        def is_auto_provided(__cls: type) -> bool:
            return __cls in auto_provide_set

    elif callable(auto_provide):
        # Looks stupid but both pyright & mypy are happy with it.
        auto_provide_callable = auto_provide

        def is_auto_provided(__cls: type) -> bool:
            return auto_provide_callable(__cls)

    else:
        raise TypeError(
            f"auto_provide must be a boolean, an iterable of classes, "
            f"or a function not {type(auto_provide)}."
        )

    auto_provided: Dict[str, object] = {}
    for arg in arguments.without_self:
        dependency = extract_auto_provided_arg_dependency(arg)
        if dependency is not None and is_auto_provided(dependency):
            auto_provided[arg.name] = dependency

    provided_dependencies = set(auto_provided.values()).union(annotated.values())
    if strict_validation and not auto_provide_set.issubset(provided_dependencies):
        raise ValueError(
            f"Some auto_provide dependencies ({auto_provide}) are not "
            f"present in the function. Found: {provided_dependencies}\n"
            f"Either ensure that auto_provide matches the function type "
            f"hints or consider specifying strict_validation=False"
        )

    return auto_provided


@API.private
def _check_valid_arg_names(
    param: str, names: Iterable[str], arguments: Arguments, strict_validation: bool
) -> None:
    for name in names:
        if not isinstance(name, str):
            raise TypeError(f"{param} expected an argument name (str), not {name!r} ({type(name)})")
        # TODO: maybe remove this check? it doesn't work well with injection before staticmethod.
        if arguments.has_self and name == arguments[0].name:
            raise ValueError(
                f"Cannot inject first argument in {param} "
                f"({arguments[0]!r}) of a method / @classmethod."
            )

        if strict_validation and name not in arguments:
            raise ValueError(f"Unknown argument in {param}: {name!r}")
