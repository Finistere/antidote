import builtins
import collections.abc as c_abc
import inspect
from typing import (Any, Dict, Iterable, Mapping, Set, TYPE_CHECKING, Union)

from .._internal import API
from .._internal.argspec import Arguments
from .._internal.wrapper import (build_wrapper, Injection, InjectionBlueprint, is_wrapper)

_BUILTINS_TYPES = {e for e in builtins.__dict__.values() if isinstance(e, type)}

if TYPE_CHECKING:
    from .injection import DEPENDENCIES_TYPE


@API.private  # Use inject instead
def raw_inject(func=None,
               *,
               arguments: Arguments = None,
               dependencies: 'DEPENDENCIES_TYPE' = None,
               use_names: Union[bool, Iterable[str]] = None,
               use_type_hints: Union[bool, Iterable[str]] = None):
    def _inject(wrapped):
        nonlocal arguments

        if inspect.isclass(wrapped):
            # @inject on a class would not return a class which is
            # counter-intuitive.
            raise TypeError("Classes cannot be wrapped with @inject. "
                            "Consider using @wire")
        if not (callable(wrapped) or isinstance(wrapped, (classmethod, staticmethod))):
            raise TypeError(f"wrapped object {wrapped} is not callable "
                            f"neither a class/static method")

        # if the function has already its dependencies injected, no need to do
        # it twice.
        if is_wrapper(wrapped):
            return wrapped

        if arguments is None:
            arguments = Arguments.from_callable(wrapped)

        blueprint = _build_injection_blueprint(
            arguments=arguments,
            dependencies=dependencies,
            use_names=use_names,
            use_type_hints=use_type_hints
        )

        # If nothing can be injected, just return the existing function without
        # any overhead.
        if blueprint.is_empty():
            return wrapped

        return build_wrapper(blueprint=blueprint, wrapped=wrapped)

    return func and _inject(func) or _inject


@API.private
def _build_injection_blueprint(arguments: Arguments,
                               dependencies: 'DEPENDENCIES_TYPE' = None,
                               use_names: Union[bool, Iterable[str]] = None,
                               use_type_hints: Union[bool, Iterable[str]] = None,
                               ) -> InjectionBlueprint:
    """
    Construct a InjectionBlueprint with all the necessary information about
    the arguments for dependency injection. Storing it avoids significant
    execution overhead./

    Used by inject()
    """
    use_names = use_names if use_names is not None else False
    use_type_hints = use_type_hints if use_type_hints is not None else True

    arg_to_dependency = _build_arg_to_dependency(arguments, dependencies)
    type_hints = _build_type_hints(arguments, use_type_hints)
    dependency_names = _build_dependency_names(arguments, use_names)

    resolved_dependencies = [
        arg_to_dependency.get(
            arg.name,
            type_hints.get(arg.name,
                           arg.name if arg.name in dependency_names else None)
        )
        for arg in arguments
    ]

    return InjectionBlueprint(tuple(
        Injection(arg_name=arg.name,
                  required=not arg.has_default,
                  dependency=dependency)
        for arg, dependency in zip(arguments, resolved_dependencies)
    ))


@API.private
def _build_arg_to_dependency(arguments: Arguments,
                             dependencies: 'DEPENDENCIES_TYPE' = None
                             ) -> Dict[str, Any]:
    from .injection import Arg
    if dependencies is None:
        arg_to_dependency: Mapping = {}
    elif isinstance(dependencies, str):
        if "{arg_name}" not in dependencies:
            raise ValueError("Missing formatting parameter {arg_name} in dependencies. "
                             "If you really want a constant injection, "
                             "consider using a defaultdict.")
        arg_to_dependency = {arg.name: dependencies.format(arg_name=arg.name)
                             for arg in arguments.without_self}
    elif callable(dependencies):
        arg_to_dependency = {arg.name: dependencies(Arg(arg.name, arg.type_hint))
                             for arg in arguments.without_self}
    elif isinstance(dependencies, c_abc.Mapping):
        _check_valid_arg_names(dependencies.keys(), arguments)
        arg_to_dependency = dependencies
    elif isinstance(dependencies, c_abc.Iterable):
        # convert to Tuple in case we cannot iterate more than once.
        dependencies = tuple(dependencies)
        if len(arguments.without_self) < len(dependencies):
            raise ValueError(f"More dependencies ({dependencies}) were provided "
                             f"than arguments ({arguments})")
        arg_to_dependency = {arg.name: dependency
                             for arg, dependency
                             in zip(arguments.without_self, dependencies)}
    else:
        raise TypeError(f'Only a mapping or a iterable is supported for '
                        f'dependencies, not {type(dependencies)!r}')

    # Remove any None as they would hide type_hints and use_names.
    return {
        k: v
        for k, v in arg_to_dependency.items()
        if v is not None
    }


@API.private
def _build_type_hints(arguments: Arguments,
                      use_type_hints: Union[bool, Iterable[str]]) -> Dict[str, Any]:
    if use_type_hints is True:
        type_hints = {arg.name: arg.type_hint for arg in arguments.without_self}
    elif use_type_hints is False:
        return {}
    elif isinstance(use_type_hints, c_abc.Iterable):
        # convert to Tuple in case we cannot iterate more than once.
        use_type_hints = tuple(use_type_hints)
        _check_valid_arg_names(use_type_hints, arguments)

        type_hints = {name: arguments[name].type_hint for name in use_type_hints}

    else:
        raise TypeError(f"Only an iterable or a boolean is supported for "
                        f"use_type_hints, not {type(use_type_hints)!r}")

    for arg_name in list(type_hints.keys()):
        type_hint = type_hints[arg_name]
        if getattr(type_hint, '__origin__', None) is Union \
                and len(type_hint.__args__) == 2:
            a = type_hint.__args__
            if isinstance(None, a[1]):
                type_hints[arg_name] = a[0]

    # Any object from builtins or typing do not carry any useful information
    # and thus must not be used as dependency IDs. So they might as well be
    # skipped entirely. Moreover they hide use_names.
    return {
        arg_name: type_hint
        for arg_name, type_hint in type_hints.items()
        if getattr(type_hint, '__module__', '') != 'typing'
           and type_hint not in _BUILTINS_TYPES  # noqa
           and type_hint is not None  # noqa
    }


@API.private
def _build_dependency_names(arguments: Arguments,
                            use_names: Union[bool, Iterable[str]]) -> Set[str]:
    if use_names is False:
        return set()
    elif use_names is True:
        return {arg.name for arg in arguments.without_self}
    elif isinstance(use_names, c_abc.Iterable):
        # convert to Tuple in case we cannot iterate more than once.
        use_names = tuple(use_names)
        _check_valid_arg_names(use_names, arguments)
        return set(use_names)
    else:
        raise TypeError(f'Only an iterable or a boolean is supported for '
                        f'use_names, not {type(use_names)!r}')


@API.private
def _check_valid_arg_names(names: Iterable[str], arguments: Arguments):
    for name in names:
        if not isinstance(name, str):
            raise TypeError(f"Expected argument name (str), "
                            f"not {type(name)}")
        if name not in arguments:
            raise ValueError(f"Unknown argument '{name}'")
        if arguments.has_self and name == arguments[0].name:
            raise ValueError(f"Cannot inject first argument "
                             f"('{arguments[0]}') of a method")
