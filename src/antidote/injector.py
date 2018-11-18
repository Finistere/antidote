import collections.abc as c_abc
import functools
import typing
from itertools import islice
from typing import (Callable, Dict, Iterable, Mapping, Optional, Sequence,
                    Tuple, Union)

from ._utils import SlotReprMixin, get_arguments_specification
from .container import DependencyContainer
from .exceptions import DependencyNotFoundError

_EMPTY_DEPENDENCY = object()


class Injection(SlotReprMixin):
    __slots__ = ('arg_name', 'required', 'dependency_id')

    def __init__(self, arg_name: str, required: bool, dependency_id):
        self.arg_name = arg_name
        self.required = required
        self.dependency_id = dependency_id


class InjectionBlueprint(SlotReprMixin):
    __slots__ = ('injections',)

    def __init__(self, injections: Sequence[Optional[Injection]]):
        self.injections = injections


class DependencyInjector:
    """
    Provides different methods to inject the dependencies from a container of
    any function.
    """

    def __init__(self, container: DependencyContainer):
        """Initialize the DependencyInjector.

        Args:
            container: :py:class:`~..DependencyContainer` from which to
                retrieve the dependencies.

        """
        self.container = container

    def __repr__(self):
        return "{}(container={!r}".format(
            type(self).__name__,
            self.container
        )

    def inject(self,
               func: Callable = None,
               arg_map: Union[Mapping, Iterable] = None,
               use_names: Union[bool, Iterable[str]] = None,
               use_type_hints: Union[bool, Iterable[str]] = None,
               ) -> Callable:
        """
        Inject the dependency into the function lazily: they are only
        retrieved upon execution.

        Args:
            func: Callable for which the argument should be injected.
            arg_map: Custom mapping of the arguments name to their respective
                dependency id. A sequence of dependencies can also be
                specified, which will be mapped to the arguments through their
                order. Annotations are overridden.
            use_names: Whether the arguments name should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments. Annotations are
                overridden, but not the arg_map.
            use_type_hints: Whether the type hints should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments.

        Returns:
            The decorator to be applied or the injected function if the
            argument :code:`func` was supplied.

        """

        def _inject(f):
            generate_args_kwargs = self._generate_args_kwargs
            bp = self._generate_injection_blueprint(func=f,
                                                    arg_map=arg_map or dict(),
                                                    use_names=use_names,
                                                    use_type_hints=use_type_hints)

            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                args, kwargs = generate_args_kwargs(bp=bp, args=args,
                                                    kwargs=kwargs)
                return f(*args, **kwargs)

            return wrapper

        return func and _inject(func) or _inject

    def bind(self,
             func: Callable = None,
             arg_map: Union[Mapping, Iterable] = None,
             use_names: Union[bool, Iterable[str]] = None,
             use_type_hints: Union[bool, Iterable[str]] = None,
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
                order. Annotations are overridden.
            use_names: Whether the arguments name should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments. Annotations are
                overridden, but not the arg_map.
            use_type_hints: Whether the type hints should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments.
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
                use_type_hints=use_type_hints,
                args=args or tuple(),
                kwargs=kwargs or dict()
            )

            return functools.partial(f, *new_args, **new_kwargs)

        return func and _bind(func) or _bind

    def call(self,
             func: Callable,
             arg_map: Union[Mapping, Iterable] = None,
             use_names: Union[bool, Iterable[str]] = None,
             use_type_hints: Union[bool, Iterable[str]] = None,
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
                order. Annotations are overridden.
            use_names: Whether the arguments name should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments. Annotations are
                overridden, but not the arg_map.
            use_type_hints: Whether the type hints should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments.
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
            use_type_hints=use_type_hints,
            args=args,
            kwargs=kwargs
        )

        return func(*new_args, **new_kwargs)

    def _inject_into_arg_kwargs(self,
                                func: Callable,
                                arg_map: Union[Mapping, Iterable] = None,
                                use_names: Union[bool, Iterable[str]] = None,
                                use_type_hints: Union[bool, Iterable[str]] = None,
                                args: Sequence = None,
                                kwargs: Dict = None
                                ) -> Tuple[Sequence, Dict]:
        """
        Utility function to generate the injection blueprint and the new
        arguments in one step.
        """
        return self._generate_args_kwargs(
            bp=self._generate_injection_blueprint(func=func,
                                                  arg_map=arg_map,
                                                  use_names=use_names,
                                                  use_type_hints=use_type_hints),
            args=args or tuple(),
            kwargs=kwargs or dict()
        )

    def _generate_args_kwargs(self,
                              bp: InjectionBlueprint,
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
        container = self.container

        for inj in islice(bp.injections, len(args), None):
            if inj is not None and inj.arg_name not in kwargs:
                try:
                    kwargs[inj.arg_name] = container[inj.dependency_id]
                except DependencyNotFoundError:
                    if inj.required:
                        raise

        return args, kwargs

    @staticmethod
    def _generate_injection_blueprint(func: Callable,
                                      arg_map: Union[Mapping, Iterable] = None,
                                      use_names: Union[bool, Iterable[str]] = None,
                                      use_type_hints: Union[bool, Iterable[str]] = None,
                                      ) -> InjectionBlueprint:
        """
        Construct a list with all the necessary information about the arguments
        for dependency injection, named the injection blueprint. Storing it
        avoids significant execution overhead.
        """
        use_names = use_names if use_names is not None else False
        use_type_hints = use_type_hints if use_type_hints is not None else True

        type_hints = None
        if use_type_hints is not False:
            try:
                type_hints = typing.get_type_hints(func)
            except Exception:
                # Python 3.5.3 does not handle properly method wrappers
                pass
        type_hints = type_hints or dict()

        if isinstance(use_type_hints, c_abc.Iterable):
            type_hints = {
                arg_name: type_hint
                for arg_name, type_hint in type_hints.items()
                if arg_name in use_type_hints
            }
        elif use_type_hints is not True and use_type_hints is not False:
            raise ValueError('Only an iterable or a boolean is supported for '
                             'use_type_hints, not {!r}'.format(use_names))

        arg_spec = get_arguments_specification(func)

        if arg_map is None:
            arg_to_dependency = {}  # type: Mapping
        elif isinstance(arg_map, c_abc.Mapping):
            arg_to_dependency = arg_map
        elif isinstance(arg_map, c_abc.Iterable):
            arg_to_dependency = {
                arg.name: dependency_id
                for arg, dependency_id in zip(arg_spec.arguments, arg_map)
            }
        else:
            raise ValueError('Only a mapping or a iterable is supported for '
                             'arg_map, not {!r}'.format(arg_map))

        if use_names is False:
            use_names = set()
        elif use_names is True:
            use_names = set(arg.name for arg in arg_spec.arguments)
        elif isinstance(use_names, c_abc.Iterable):
            use_names = set(use_names)
        else:
            raise ValueError('Only an iterable or a boolean is supported for '
                             'use_names, not {!r}'.format(use_names))

        dependencies = [
            arg_to_dependency.get(arg.name,
                                  arg.name
                                  if arg.name in use_names else
                                  type_hints.get(arg.name, _EMPTY_DEPENDENCY))
            for arg in arg_spec.arguments
        ]

        return InjectionBlueprint(tuple([
            Injection(arg_name=arg.name,
                      required=not arg.has_default,
                      dependency_id=dependency_id)
            if dependency_id is not _EMPTY_DEPENDENCY else
            None
            for arg, dependency_id in zip(arg_spec.arguments, dependencies)
        ]))
