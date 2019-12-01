import builtins
import collections.abc as c_abc
from typing import (Any, Callable, Dict, Hashable, Iterable, Mapping, overload, Set,
                    TypeVar, Union)

from .._internal.argspec import Arguments
from .._internal.default_container import get_default_container
from .._internal.wrapper import InjectedWrapper, Injection, InjectionBlueprint
from ..core import DependencyContainer

F = TypeVar('F', Callable, staticmethod, classmethod)

_BUILTINS_TYPES = {e for e in builtins.__dict__.values() if isinstance(e, type)}
DEPENDENCIES_TYPE = Union[
    Mapping[str, Hashable],  # {arg_name: dependency, ...}
    Iterable[Hashable],  # (dependency for arg 1, ...)
    Callable[[str], Hashable],  # arg_name -> dependency
    str  # str.format(arg_name=arg_name) -> dependency
]


@overload
def inject(func: F,  # noqa: E704  # pragma: no cover
           *,
           arguments: Arguments = None,
           dependencies: DEPENDENCIES_TYPE = None,
           use_names: Union[bool, Iterable[str]] = None,
           use_type_hints: Union[bool, Iterable[str]] = None,
           container: DependencyContainer = None
           ) -> F: ...


@overload
def inject(*,  # noqa: E704  # pragma: no cover
           arguments: Arguments = None,
           dependencies: DEPENDENCIES_TYPE = None,
           use_names: Union[bool, Iterable[str]] = None,
           use_type_hints: Union[bool, Iterable[str]] = None,
           container: DependencyContainer = None
           ) -> Callable[[F], F]: ...


def inject(func=None,
           *,
           arguments: Arguments = None,
           dependencies: DEPENDENCIES_TYPE = None,
           use_names: Union[bool, Iterable[str]] = None,
           use_type_hints: Union[bool, Iterable[str]] = None,
           container: DependencyContainer = None
           ):
    """
    Inject the dependencies into the function lazily, they are only retrieved
    upon execution. Can be used as a decorator.

    Dependency CAN NOT be:

    - part of the builtins
    - part of typing
    - None

    Args:
        func: Callable to be wrapped.
        arguments: Arguments of the function can directly be specified if they
            have already been built.
        dependencies: Can be either a mapping of arguments name to their
            dependency, an iterable of dependencies or a function which returns
            the dependency given the arguments name. If an iterable is specified,
            the position of the arguments is used to determine their respective
            dependency. An argument may be skipped by using :code:`None` as a
            placeholder. Type hints are overridden. Defaults to :code:`None`.
        use_names: Whether or not the arguments' name should be used as their
            respective dependency. An iterable of argument names may also be
            supplied to restrict this to those. Defaults to :code:`False`.
        use_type_hints: Whether or not the type hints (annotations) should be
            used as the arguments dependency. An iterable of argument names may
            also be specified to restrict this to those. Any type hints from
            the builtins (str, int...) or the typing (:py:class:`~typing.Optional`,
            ...) are ignored. Defaults to :code:`True`.
        container: :py:class:`~.core.container.DependencyContainer` from which
            the dependencies should be retrieved. Defaults to the global
            core if it is defined.

    Returns:
        The decorator to be applied or the injected function if the
        argument :code:`func` was supplied.

    """

    def _inject(wrapped):
        nonlocal arguments
        # if the function has already its dependencies injected, no need to do
        # it twice.
        if isinstance(wrapped, InjectedWrapper):
            return wrapped

        if arguments is None:
            arguments = Arguments.from_method(wrapped)

        blueprint = _build_injection_blueprint(
            arguments=arguments,
            dependencies=dependencies,
            use_names=use_names,
            use_type_hints=use_type_hints
        )

        # If nothing can be injected, just return the existing function without
        # any overhead.
        if all(injection.dependency is None for injection in blueprint.injections):
            return wrapped

        return InjectedWrapper(container=container or get_default_container(),
                               blueprint=blueprint,
                               wrapped=wrapped)

    return func and _inject(func) or _inject


def _build_injection_blueprint(arguments: Arguments,
                               dependencies: DEPENDENCIES_TYPE = None,
                               use_names: Union[bool, Iterable[str]] = None,
                               use_type_hints: Union[bool, Iterable[str]] = None,
                               ) -> InjectionBlueprint:
    """
    Construct a InjectionBlueprint with all the necessary information about
    the arguments for dependency injection. Storing it avoids significant
    execution overhead.

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

    return InjectionBlueprint(tuple([
        Injection(arg_name=arg.name,
                  required=not arg.has_default,
                  dependency=dependency)
        for arg, dependency in zip(arguments, resolved_dependencies)
    ]))


def _build_arg_to_dependency(arguments: Arguments,
                             dependencies: DEPENDENCIES_TYPE = None
                             ) -> Dict[str, Any]:
    if dependencies is None:
        arg_to_dependency = {}  # type: Mapping
    elif isinstance(dependencies, str):
        arg_to_dependency = {arg.name: dependencies.format(arg_name=arg.name)
                             for arg in arguments}
    elif callable(dependencies):
        arg_to_dependency = {arg.name: dependencies(arg.name)
                             for arg in arguments}
    elif isinstance(dependencies, c_abc.Mapping):
        for name in dependencies.keys():
            if name not in arguments:
                raise ValueError("Unknown argument {!r}".format(name))

        arg_to_dependency = dependencies
    elif isinstance(dependencies, c_abc.Iterable):
        dependencies = tuple(dependencies)
        if len(arguments) < len(dependencies):
            raise ValueError("More dependencies were provided than arguments")

        arg_to_dependency = {arg.name: dependency
                             for arg, dependency
                             in zip(arguments, dependencies)}
    else:
        raise ValueError('Only a mapping or a iterable is supported for '
                         'arg_map, not {!r}'.format(type(dependencies)))

    # Remove any None as they would hide type_hints and use_names.
    return {
        k: v
        for k, v in arg_to_dependency.items()
        if v is not None
    }


def _build_type_hints(arguments: Arguments,
                      use_type_hints: Union[bool, Iterable[str]]) -> Dict[str, Any]:
    if use_type_hints is True:
        type_hints = {arg.name: arg.type_hint for arg in arguments}
    elif use_type_hints is False:
        return {}
    elif isinstance(use_type_hints, c_abc.Iterable):
        use_type_hints = tuple(use_type_hints)
        for name in use_type_hints:
            if name not in arguments:
                raise ValueError("Unknown argument {!r}".format(name))

        type_hints = {name: arguments[name].type_hint for name in use_type_hints}

    else:
        raise ValueError('Only an iterable or a boolean is supported for '
                         'use_type_hints, not {!r}'.format(type(use_type_hints)))

    # Any object from builtins or typing do not carry any useful information
    # and thus must not be used as dependency IDs. So they might as well be
    # skipped entirely. Moreover they hide use_names.
    return {
        arg_name: type_hint
        for arg_name, type_hint in type_hints.items()
        if getattr(type_hint, '__module__', '') != 'typing'
           and type_hint not in _BUILTINS_TYPES  # noqa
           and type_hint is not None
    }


def _build_dependency_names(arguments: Arguments,
                            use_names: Union[bool, Iterable[str]]) -> Set[str]:
    if use_names is False:
        return set()
    elif use_names is True:
        return {arg.name for arg in arguments}
    elif isinstance(use_names, c_abc.Iterable):
        use_names = tuple(use_names)
        for name in use_names:
            if name not in arguments:
                raise ValueError("Unknown argument {!r}".format(name))

        return set(use_names)
    else:
        raise ValueError('Only an iterable or a boolean is supported for '
                         'use_names, not {!r}'.format(type(use_names)))
