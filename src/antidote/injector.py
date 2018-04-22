import functools
import typing
from itertools import islice
from typing import (
    Any, Callable, Dict, Iterable, Mapping, Sequence, Tuple,
    Union
)

from ._utils import get_arguments_specification
from .container import DependencyContainer, DependencyNotFoundError

_EMPTY_DEPENDENCY = object()

InjectionBlueprintType = Tuple[Tuple[str, bool, Any], ...]


class DependencyInjector:
    """
    Provides different methods to inject the dependencies from a container of
    any function.
    """

    def __init__(self, container: DependencyContainer) -> None:
        """Initialize the DependencyInjector.

        Args:
            container: :py:class:`~..DependencyContainer` from which to
                retrieve the dependencies.

        """
        self._container = container

    def __repr__(self):
        return "{}(container={!r}".format(
            type(self).__name__,
            self._container
        )

    def inject(self,
               func: Callable = None,
               arg_map: Union[Mapping, Iterable] = None,
               use_names: Union[bool, Iterable[str]] = False
               ) -> Callable:
        """
        Inject the dependency into the function lazily: they are only
        retrieved upon execution.

        Args:
            func: Callable for which the argument should be injected.
            arg_map: Custom mapping of the arguments name to their respective
                dependency id. A sequence of dependencies can also be
                specified, which will be mapped to the arguments through their
                order. Annotations are overriden.
            use_names: Whether the arguments name should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments. Annotations are
                overriden, but not the arg_map.

        Returns:
            The decorator to be applied or the injected function if the
            argument :code:`func` was supplied.

        """

        def _inject(f):
            generate_args_kwargs = self._generate_args_kwargs
            injection_blueprint = self._generate_injection_blueprint(
                func=f,
                arg_map=arg_map or dict(),
                use_names=use_names
            )

            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                args, kwargs = generate_args_kwargs(
                    injection_blueprint=injection_blueprint,
                    args=args,
                    kwargs=kwargs
                )

                return f(*args, **kwargs)

            return wrapper

        return func and _inject(func) or _inject

    def bind(self,
             func: Callable = None,
             arg_map: Union[Mapping, Iterable] = None,
             use_names: Union[bool, Iterable[str]] = False,
             args: Sequence = None,
             kwargs: Dict = None
             ) -> Callable:
        """
        Creates a partial function with the injected arguments. It may be used
        whenever a function is called repeatedly, to diminish the runtime
        impact.

        Beware that this makes testing your function troublesome as you won't
        be able to change the dependencies used once imported.

        Args:
            func: Callable for which the argument should be injected.
            arg_map: Custom mapping of the arguments name to their respective
                dependency id. A sequence of dependencies can also be
                specified, which will be mapped to the arguments through their
                order. Annotations are overriden.
            use_names: Whether the arguments name should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments. Annotations are
                overriden, but not the arg_map.
            args: Positional arguments passed on the function, overriding any
                injection, which will also be bound.
            kwargs: Keyword arguments passed on the function, overriding any
                injection, which will also be bound.

        Returns:
            The decorator to be applied or the injected function if the
            argument :code:`func` was supplied.

        """

        def _bind(f):
            new_args, new_kwargs = self._inject_into_arg_kwargs(
                func=f,
                arg_map=arg_map,
                use_names=use_names,
                args=args or tuple(),
                kwargs=kwargs or dict()
            )

            return functools.partial(f, *new_args, **new_kwargs)

        return func and _bind(func) or _bind

    def call(self,
             func: Callable,
             arg_map: Union[Mapping, Iterable] = None,
             use_names: Union[bool, Iterable[str]] = False,
             args: Sequence = None,
             kwargs: Dict = None
             ) -> Callable:
        """
        Call a function with specified arguments and keyword arguments.
        Dependencies are injected whenever necessary.

        Args:
            func: Callable for which the argument should be injected.
            arg_map: Custom mapping of the arguments name to their respective
                dependency id. A sequence of dependencies can also be
                specified, which will be mapped to the arguments through their
                order. Annotations are overriden.
            use_names: Whether the arguments name should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments. Annotations are
                overriden, but not the arg_map.
            args: Positional arguments passed on the function, overriding any
                injection.
            kwargs: Keyword arguments passed on the function, overriding any
                injection.

        Returns:
            The decorator to be applied or the injected function if the
            argument :code:`func` was supplied.

        """

        new_args, new_kwargs = self._inject_into_arg_kwargs(
            func=func,
            arg_map=arg_map,
            use_names=use_names,
            args=args,
            kwargs=kwargs
        )

        return func(*new_args, **new_kwargs)

    def _inject_into_arg_kwargs(self,
                                func: Callable,
                                arg_map: Union[Mapping, Iterable] = None,
                                use_names: Union[bool, Iterable[str]] = False,
                                args: Sequence = None,
                                kwargs: Dict = None
                                ) -> Tuple[Sequence, Dict]:
        """
        Utility function to generate the injection blueprint and the new
        arguments in one step.
        """
        return self._generate_args_kwargs(
            injection_blueprint=self._generate_injection_blueprint(
                func=func,
                arg_map=arg_map,
                use_names=use_names
            ),
            args=args or tuple(),
            kwargs=kwargs or dict()
        )

    def _generate_args_kwargs(self,
                              injection_blueprint: InjectionBlueprintType,
                              args: Sequence,
                              kwargs: Dict
                              ) -> Tuple[Sequence, Dict]:
        """
        Generate the new arguments to be used by retrieving the missing
        dependencies based on the injection blueprint.

        If one argument has no default, is not set and is not mapped to a
        known dependency, :py:exc:`~..exceptions.DependencyNotFoundError` is
        raised.
        """
        kwargs = kwargs.copy()
        container = self._container

        for arg_name, has_default, dependency_id \
                in islice(injection_blueprint, len(args), None):
            if dependency_id is not _EMPTY_DEPENDENCY \
                    and arg_name not in kwargs:
                try:
                    kwargs[arg_name] = container[dependency_id]
                except DependencyNotFoundError:
                    if has_default is False:
                        raise

        return args, kwargs

    @staticmethod
    def _generate_injection_blueprint(func: Callable,
                                      arg_map: Union[Mapping, Iterable],
                                      use_names: Union[bool, Iterable[str]]
                                      ) -> InjectionBlueprintType:
        """
        Construct a list with all the necessary information about the arguments
        for dependency injection, named the injection blueprint. Storing it
        avoids significant execution overhead.

        The blueprint looks like:

        >>> [
        ...    (
        ...        'arg1',  # Name of the argument
        ...         False,  # whether it has a default value
        ...         'dependency id'  # associated dependency id
        ...     ),
        ...    ('arg2', True, _EMPTY_DEPENDENCY)
        ... ]

        """
        from collections import Mapping, Iterable

        try:
            annotations = typing.get_type_hints(func) or dict()
        except Exception:
            # Python 3.5.3 does not handle properly method wrappers
            annotations = dict()

        arg_spec, _, _ = get_arguments_specification(func)

        if arg_map is None:
            arg_to_dependency = {}  # type: Mapping
        elif isinstance(arg_map, Mapping):
            arg_to_dependency = arg_map
        elif isinstance(arg_map, Iterable):
            arg_to_dependency = {
                name: dependency_id
                for (name, _), dependency_id in zip(arg_spec, arg_map)
            }
        else:
            raise ValueError('Only a mapping or a iterable is supported for '
                             'arg_map, not {!r}'.format(arg_map))

        if use_names is None or use_names is False:
            use_names = set()
        elif use_names is True:
            use_names = set(e[0] for e in arg_spec)
        elif isinstance(use_names, Iterable):
            use_names = set(use_names)
        else:
            raise ValueError('Only an iterable or a boolean is supported for '
                             'use_names, not {!r}'.format(use_names))

        return tuple(
            (
                name,
                has_default,
                arg_to_dependency.get(
                    name,
                    name
                    if name in use_names else
                    annotations.get(name, _EMPTY_DEPENDENCY)
                ),
            )
            for name, has_default in arg_spec
        )
