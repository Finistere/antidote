import typing
from itertools import islice
from typing import (
    Callable, Dict, Iterable, List, Mapping, Sequence, Tuple,
    Union
)

import functools

from ._compat import get_arguments_specification, functools_wraps
from .container import DependencyContainer, DependencyNotFoundError

_EMPTY_DEPENDENCY = object()


class DependencyInjector(object):
    """
    Injects the dependencies from a container before building an object or
    calling a function.
    """

    def __init__(self, container):
        # type: (DependencyContainer) -> None
        """Initialize the DependencyInjector.

        Args:
            container: Object with :code:`__getitem__()` defined to retrieve
                the dependencies. :py:exc:`.DependencyNotFoundError` should
                be raised whenever a dependency could not be found.

        """
        self._container = container

    def __repr__(self):
        return "{}(container={!r}".format(
            type(self).__name__,
            self._container
        )

    def inject(self, func=None, mapping=None, use_names=False):
        # type: (Callable, Mapping, Union[bool, Iterable[str]]) -> Callable
        """Inject the dependency into the function.

        Args:
            func (callable): Callable for which the argument should be
                injected.
            mapping (dict, optional): Custom mapping of the arguments name
                to their respective dependency id. Overrides annotations.
                Defaults to None.
            use_names (bool, optional): Whether the arguments name
                should be used to search for a dependency when no mapping,
                nor annotation is found. Defaults to False.

        Returns:
            callable: The decorator to be applied.

        """
        generate_args_kwargs = self._generate_args_kwargs

        def _inject(f):
            # Using nonlocal would be ideal.
            non_local = [None]  # type: List[Sequence]

            @functools_wraps(f)
            def wrapper(*args, **kwargs):
                if non_local[0] is None:
                    non_local[0] = self._generate_injection_blueprint(
                        func=f,
                        use_names=use_names,
                        mapping=mapping or dict()
                    )

                args, kwargs = generate_args_kwargs(
                    args=args,
                    kwargs=kwargs,
                    injection_blueprint=non_local[0]
                )

                return f(*args, **kwargs)

            return wrapper

        return func and _inject(func) or _inject

    def bind(self,
             func=None,  # type: Callable
             use_names=False,  # type: Union[bool, Iterable[str]]
             mapping=None,  # type: Mapping
             args=None,  # type: Sequence
             kwargs=None  # type: Dict
             ):
        # type: (...) -> Callable
        """
        Creates a partial function with the injected arguments.

        It should be used whenever a function is called repeatedly.

        Args:
            func (callable): Callable for which the argument should be
                injected.
            use_names (bool, optional): Whether the arguments name
                should be used to search for a dependency when no mapping,
                nor annotation is found. Defaults to False.
            mapping (dict, optional): Custom mapping of the arguments name
                to their respective dependency id. Overrides annotations.
                Defaults to None.
            args (iterable, optional): Positional arguments which override any
                injection. Defaults to None.
            kwargs (dict, optional): Keyword arguments which override any
                injection. Defaults to None.

        Returns:
            callable: Partial function with its dependencies injected.

        """

        def _bind(f):
            new_args, new_kwargs = self._inject_into_arg_kwargs(
                func=f,
                use_names=use_names,
                mapping=mapping or dict(),
                args=args or tuple(),
                kwargs=kwargs or dict()
            )

            return functools.partial(f, *new_args, **new_kwargs)

        return func and _bind(func) or _bind

    def call(self,
             func,  # type: Callable
             use_names=False,  # type: Union[bool, Iterable[str]]
             mapping=None,  # type: Mapping
             args=None,  # type: Sequence
             kwargs=None  # type: Dict
             ):
        # type: (...) -> Callable
        """
        Call a function with specified arguments and keyword arguments.
        Dependencies are injected if not satisfied.

        Args:
            func (callable): Callable for which the argument should be
                injected.
            use_names (bool, optional): Whether the arguments name
                should be used to search for a dependency when no mapping,
                nor annotation is found. Defaults to False.
            mapping (dict, optional): Custom mapping of the arguments name
                to their respective dependency id. Overrides annotations.
                Defaults to None.
            args (iterable, optional): Positional arguments which override any
                injection. Defaults to None.
            kwargs (dict, optional): Keyword arguments which override any
                injection. Defaults to None.

        Returns:
            Returns whatever the function returns.

        """

        new_args, new_kwargs = self._inject_into_arg_kwargs(
            func=func,
            use_names=use_names,
            mapping=mapping or dict(),
            args=args or tuple(),
            kwargs=kwargs or dict()
        )

        return func(*new_args, **new_kwargs)

    def _inject_into_arg_kwargs(self,
                                func,  # type: Callable
                                use_names,  # type: Union[bool, Iterable[str]]
                                mapping,  # type: Mapping
                                args,  # type: Sequence
                                kwargs  # type: Dict
                                ):
        # type: (...) -> Tuple[Sequence, Dict]
        """
        Utility function to generate the injection blueprint and the new
        arguments in one step.
        """
        return self._generate_args_kwargs(
            args=args or tuple(),
            kwargs=kwargs or dict(),
            injection_blueprint=self._generate_injection_blueprint(
                func=func,
                mapping=mapping or dict(),
                use_names=use_names
            )
        )

    def _generate_args_kwargs(self, args, kwargs, injection_blueprint):
        # type: (Sequence, Dict, Sequence) -> Tuple[Sequence, Dict]
        """
        Generate the new arguments to be injected by retrieving all
        dependencies defined in the blueprint if it is not set by the passed
        arguments.

        Raises DependencyNotFoundError if an argument is neither set nor its
        associated dependency found in the container and has no default.
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

    @classmethod
    def _generate_injection_blueprint(cls, func, use_names, mapping):
        # No type hints yet. Mypy does not handle properly the conversion of
        # use_names to a set and typing.get_type_hints raises an error as it
        # lacks typing information.
        """
        Generate a blueprint for injection, so the injection itself can be done
        as fast as possible.

        The blueprint itself has the form of:
        [
            [name (str), dependency_id (object), has_default (bool)]
            for argument in arguments of func
        ]
        """
        try:
            argument_mapping = typing.get_type_hints(func) or dict()
        except Exception:
            # Python 3.5.3 does not handle properly method wrappers
            argument_mapping = dict()

        try:
            del argument_mapping['return']
        except KeyError:
            pass
        argument_mapping.update(mapping)

        arg_spec, _, _ = get_arguments_specification(func)

        use_names = set(
            (e[0] for e in arg_spec)
            if use_names is True else
            use_names or []
        )

        return tuple(
            (
                name,
                has_default,
                argument_mapping.get(
                    name,
                    name if name in use_names else _EMPTY_DEPENDENCY
                ),
            )
            for name, has_default in arg_spec
        )
