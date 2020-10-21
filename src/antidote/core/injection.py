import builtins
import collections.abc as c_abc
import inspect
from typing import (Any, Callable, Dict, final, Hashable, Iterable, Mapping,
                    Optional,  overload,  Sequence, Set, TypeVar, Union)

from .._internal import API
from .._internal.argspec import Arguments
from .._internal.utils import FinalImmutable
from .._internal.wrapper import (build_wrapper, InjectedWrapper,
                                 Injection, InjectionBlueprint)

F = TypeVar('F', Callable, staticmethod, classmethod)

_BUILTINS_TYPES = {e for e in builtins.__dict__.values() if isinstance(e, type)}


@API.public
@final
class Arg(FinalImmutable):
    """
    Represents an argument (name and type hint) if you need a very custom injection
    logic.
    """
    __slots__ = ('name', 'type_hint')
    name: str
    type_hint: Any

    def __init__(self, name: str, type_hint: Any):
        super().__init__(name=name, type_hint=type_hint)


# This type is experimental.
DEPENDENCIES_TYPE = Union[
    Mapping[str, Hashable],  # {arg_name: dependency, ...}
    Sequence[Optional[Hashable]],  # (dependency for arg 1, ...)
    Callable[[Arg], Optional[Hashable]],  # arg -> dependency
    str  # str.format(arg_name=arg_name) -> dependency
]


@overload
def inject(func: F,  # noqa: E704  # pragma: no cover
           *,
           dependencies: DEPENDENCIES_TYPE = None,
           use_names: Union[bool, Iterable[str]] = None,
           use_type_hints: Union[bool, Iterable[str]] = None
           ) -> F: ...


@overload
def inject(*,  # noqa: E704  # pragma: no cover
           dependencies: DEPENDENCIES_TYPE = None,
           use_names: Union[bool, Iterable[str]] = None,
           use_type_hints: Union[bool, Iterable[str]] = None
           ) -> Callable[[F], F]: ...


@API.public
def inject(func=None,
           *,
           dependencies: DEPENDENCIES_TYPE = None,
           use_names: Union[bool, Iterable[str]] = None,
           use_type_hints: Union[bool, Iterable[str]] = None):
    """
    Inject the dependencies into the function lazily, they are only retrieved
    upon execution. As several options can apply to the same argument, the priority is
    defined as:

    1. Dependencies declared explicitly if any declared with :code:`dependencies`.
    2. Type hints (unless deactivated through :code:`use_type_hints`)
    3. Argument names if specified with :code:`use_names`

    .. doctest:: core_inject

        >>> from antidote import inject
        >>> # All possibilities for dependency argument.
        ... @inject(dependencies=None)  # default
        ... def f(a):
        ...     pass  # a = <not injected>
        >>> @inject(dependencies=dict(b='dependency'))
        ... def f(a, b):
        ...     pass  # a, b = <not injected>, world.get('dependency')
        >>> @inject(dependencies=[None, 'dependency'])  # Nothing will be injected a
        ... def f(a, b):
        ...     pass  # a, b = <not injected>, world.get('dependency')
        >>> @inject(dependencies=lambda arg: 'dependency' if arg.name == 'b' else None)
        ... def f(a, b):
        ...     pass  # a, b = <not injected>, world.get('dependency')
        >>> @inject(dependencies="conf:{arg_name}")
        ... def f(a):
        ...     pass  # a = world.get('conf:a')
        >>> # All possibilities for use_names argument.
        ... @inject(use_names=False)  # default
        ... def f(a):
        ...     pass  # a = <not injected>
        >>> @inject(use_names=True)
        ... def f(a):
        ...     pass  # a = world.get('a')
        >>> @inject(use_names=['b'])
        ... def f(a, b):
        ...     pass  # a, b = <not injected>, world.get('b')
        >>> # All possibilities for use_type_hints argument.
        ... class Service:
        ...     pass
        >>> @inject(use_type_hints=True)  # default
        ... def f(a: Service):
        ...     pass  # a = world.get(Service)
        >>> @inject(use_type_hints=['b'])
        ... def f(a: Service, b: Service):
        ...     pass  # a, b = <not injected>, world.get(Service)
        >>> @inject(use_type_hints=False)
        ... def f(a: Service):
        ...     pass  # a = <not injected>

    Args:
        func: Callable to be wrapped. Can also be used on static methods or class methods.
        dependencies: Explicit definition of the dependencies which overrides
            :code:`use_names` and :code:`use_type_hints`. Defaults to :py:obj:`None`.
            Can be one of:

            - Mapping from argument name to its dependency
            - Sequence of dependencies which will be mapped with the position
              of the arguments. :py:obj:`None` can be used as a placeholder.
            - Callable which receives :py:class:`~.Arg` as arguments and should
              return the matching dependency. :py:obj:`None` should be used for
              arguments without dependency.
            - String which must have :code:`{arg_name}` as format parameter
        use_names: Whether or not the arguments' name should be used as their
            respective dependency. An iterable of argument names may also be
            supplied to activate this feature only for those. Defaults to :code:`False`.
        use_type_hints: Whether or not the type hints should be used as the arguments
            dependency. An iterable of argument names may also be supplied to activate
            this feature only for those. Any type hints from the builtins (str, int...)
            or the typing (except :py:class:`~typing.Optional`) are ignored. It overrides
            :code:`use_names`. Defaults to :code:`True`.

    Returns:
        The decorator to be applied or the injected function if the
        argument :code:`func` was supplied.

    """

    return raw_inject(func,
                      dependencies=dependencies,
                      use_names=use_names,
                      use_type_hints=use_type_hints)


@API.experimental  # Function will be kept in sync with @inject, so you may use it.
def validate_injection(dependencies: DEPENDENCIES_TYPE = None,
                       use_names: Union[bool, Iterable[str]] = None,
                       use_type_hints: Union[bool, Iterable[str]] = None):
    if not (dependencies is None
            or isinstance(dependencies, (str, c_abc.Sequence, c_abc.Mapping))
            or callable(dependencies)):
        raise TypeError(
            f"dependencies can be None, a mapping of arguments names to dependencies, "
            f"a sequence of dependencies, a function or a string, "
            f"not a {type(dependencies)!r}"
        )
    if isinstance(dependencies, str):
        if "{arg_name}" not in dependencies:
            raise ValueError("Missing formatting parameter {arg_name} in dependencies. "
                             "If you really want a constant injection, "
                             "consider using a defaultdict.")
    if isinstance(dependencies, c_abc.Mapping):
        if not all(isinstance(k, str) for k in dependencies.keys()):
            raise TypeError("Dependencies keys must be argument names (str)")

    if not (use_names is None or isinstance(use_names, (bool, c_abc.Iterable))):
        raise TypeError(
            f"use_names must be either a boolean or a whitelist of argument names, "
            f"not {type(use_names)!r}.")
    if isinstance(use_names, c_abc.Iterable):
        if not all(isinstance(arg_name, str) for arg_name in use_names):
            raise TypeError("use_names must be list of argument names (str) or a boolean")

    if not (use_type_hints is None or isinstance(use_type_hints,
                                                 (bool, c_abc.Iterable))):
        raise TypeError(
            f"use_type_hints must be either a boolean or a whitelist of argument names, "
            f"not {type(use_type_hints)!r}.")
    if isinstance(use_type_hints, c_abc.Iterable):
        if not all(isinstance(arg_name, str) for arg_name in use_type_hints):
            raise TypeError(
                "use_type_hints must be list of argument names (str) or a boolean")


@API.private  # Use inject instead
def raw_inject(func=None,
               *,
               arguments: Arguments = None,
               dependencies: DEPENDENCIES_TYPE = None,
               use_names: Union[bool, Iterable[str]] = None,
               use_type_hints: Union[bool, Iterable[str]] = None):
    def _inject(wrapped):
        if inspect.isclass(wrapped):
            # @inject on a class would not return a class which is
            # counter-intuitive.
            raise TypeError("Classes cannot be wrapped with @inject. "
                            "Consider using @wire")
        if not (callable(wrapped) or isinstance(wrapped, (classmethod, staticmethod))):
            raise TypeError(f"wrapped object {wrapped} is not callable "
                            f"neither a class/static method")

        nonlocal arguments
        # if the function has already its dependencies injected, no need to do
        # it twice.
        if isinstance(wrapped, InjectedWrapper):
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
        if all(injection.dependency is None for injection in blueprint.injections):
            return wrapped

        return build_wrapper(blueprint=blueprint, wrapped=wrapped)

    return func and _inject(func) or _inject


@API.private
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

    return InjectionBlueprint(tuple(
        Injection(arg_name=arg.name,
                  required=not arg.has_default,
                  dependency=dependency)
        for arg, dependency in zip(arguments, resolved_dependencies)
    ))


@API.private
def _build_arg_to_dependency(arguments: Arguments,
                             dependencies: DEPENDENCIES_TYPE = None
                             ) -> Dict[str, Any]:
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
            if a[1] is type(None):
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
