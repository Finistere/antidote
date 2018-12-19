import collections.abc as c_abc
import typing
from functools import wraps
from typing import Any, Callable, Dict, Iterable, Mapping, Set, Union

from .wrapper import InjectedCallableWrapper, Injection, InjectionBlueprint
from .._internal.argspec import Arguments, get_arguments_specification
from .._internal.global_container import get_global_container
from ..container import DependencyContainer


def inject(func: Callable = None,
           arg_map: Union[Mapping, Iterable] = None,
           use_names: Union[bool, Iterable[str]] = None,
           use_type_hints: Union[bool, Iterable[str]] = None,
           container: DependencyContainer = None
           ) -> Callable:
    """
    Inject the dependency into the function lazily, they are only retrieved
    upon execution. Can be used as a decorator.

    Args:
        func: Callable to be wrapped.
        arg_map: Can be either a mapping of arguments name to their dependency
            id, or an iterable of dependency ids. Their position is used to
            determine the respective argument. An argument may be skipped by
            using `None` as as placeholder. Type hints are overridden. Defaults
            to :code:`None`.
        use_names: Whether or not the arguments' name should be used as
            dependency ids. An iterable of argument names may also be
            supplied to restrict this to those. Defaults to :code:`False`.
        use_type_hints: Whether or not the type hints (annotations) should be
            used as dependency ids. An iterable of argument names may also be
            supplied to restrict this to those. Any type hints from the
            builtins (str, int...) or the typing (:py:class:`~typing.Optional`,
            ...) are ignored. Defaults to :code:`True`.
        container: :py:class:~.container.base.DependencyContainer` from which
            the dependencies should be retrieved. Defaults to the global
            container if it is defined.

    Returns:
        The decorator to be applied or the injected function if the
        argument :code:`func` was supplied.

    """

    def _inject(wrapped):
        # if the function has already its dependencies injected, no need to do
        # it twice.
        if isinstance(wrapped, InjectedCallableWrapper):
            return wrapped

        wrapper = InjectedCallableWrapper(
            container=container or get_global_container(),
            blueprint=_build_injection_blueprint(
                func=wrapped,
                arg_map=arg_map,
                use_names=use_names,
                use_type_hints=use_type_hints
            ),
            wrapped=wrapped
        )
        return wraps(wrapped, updated=[])(wrapper)

    return func and _inject(func) or _inject


def _build_injection_blueprint(func: Callable,
                               arg_map: Union[Mapping, Iterable] = None,
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

    arguments = get_arguments_specification(func)
    arg_to_dependency = _build_arg_to_dependency(arguments, arg_map)
    type_hints = _build_type_hints(func, use_type_hints)
    dependency_names = _build_dependency_names(arguments, use_names)

    dependencies = [
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
                  dependency_id=dependency_id)
        for arg, dependency_id in zip(arguments, dependencies)
    ]))


def _build_arg_to_dependency(arguments: Arguments,
                             arg_map: Union[Mapping, Iterable] = None
                             ) -> Dict[str, Any]:
    if arg_map is None:
        arg_to_dependency = {}  # type: Mapping
    elif isinstance(arg_map, c_abc.Mapping):
        arg_to_dependency = arg_map
    elif isinstance(arg_map, c_abc.Iterable):
        arg_to_dependency = {arg.name: dependency_id
                             for arg, dependency_id
                             in zip(arguments, arg_map)}
    else:
        raise ValueError('Only a mapping or a iterable is supported for '
                         'arg_map, not {!r}'.format(type(arg_map)))

    # Remove any None as they would hide type_hints and use_names.
    return {
        k: v
        for k, v in arg_to_dependency.items()
        if v is not None
    }


def _build_type_hints(func: Callable,
                      use_type_hints: Union[bool, Iterable[str]]) -> Dict[str, Any]:
    type_hints = None
    if use_type_hints is not False:
        try:
            type_hints = typing.get_type_hints(func)
        except Exception:  # Python 3.5.3 does not handle properly method wrappers
            pass
    type_hints = type_hints or dict()

    if isinstance(use_type_hints, c_abc.Iterable):
        type_hints = {arg_name: type_hint
                      for arg_name, type_hint in type_hints.items()
                      if arg_name in use_type_hints}
    elif use_type_hints is not True and use_type_hints is not False:
        raise ValueError('Only an iterable or a boolean is supported for '
                         'use_type_hints, not {!r}'.format(type(use_type_hints)))

    # Any object from builtins or typing do not carry any useful information
    # and thus must not be used as dependency IDs. So they might as well be
    # skipped entirely. Moreover they hide use_names.
    return {
        arg_name: type_hint
        for arg_name, type_hint in type_hints.items()
        if getattr(type_hint, '__module__', '') not in {'typing', 'builtins'}
    }


def _build_dependency_names(arguments: Arguments,
                            use_names: Union[bool, Iterable[str]]) -> Set[str]:
    if use_names is False:
        return set()
    elif use_names is True:
        return set(arg.name for arg in arguments)
    elif isinstance(use_names, c_abc.Iterable):
        return set(use_names)
    else:
        raise ValueError('Only an iterable or a boolean is supported for '
                         'use_names, not {!r}'.format(type(use_names)))
