import functools
import inspect
from collections import OrderedDict
from itertools import islice

import wrapt

from ._compat import PY3
from .exceptions import *

_EMPTY_DEPENDENCY = object()


class DependencyInjector(object):
    """
    Injects the dependencies from a container before building an object or
    calling a function.
    """

    def __init__(self, container):
        """Initialize the DependencyInjector.

        Args:
            container: Object with :code:`__getitem__()` defined to retrieve
                the dependencies. :py:exc:`.DependencyNotFoundError` should
                be raised whenever a dependency could not be found.

        """
        self._container = container

    def inject(self, mapping=None, use_arg_name=False):
        """Inject the dependency into the function.

        Args:
            mapping (dict, optional): Custom mapping of the arguments name
                to their respective dependency id. Overrides annotations.
                Defaults to None.
            use_arg_name (bool, optional): Whether the arguments name
                should be used to search for a dependency when no mapping,
                nor annotation is found. Defaults to False.

        Returns:6
            callable: The injected function.

        """

        mapping = mapping or dict()
        gen_args_kwargs = self._generate_args_kwargs
        # Using nonlocal would be better for Python 3.
        arg_mapping_container = [None]

        @wrapt.decorator
        def fast_inject(wrapped, _, args, kwargs):
            if arg_mapping_container[0] is None:
                arg_mapping_container[0] = self._generate_arguments_mapping(
                    func=wrapped,
                    use_arg_name=use_arg_name,
                    mapping=mapping
                )

            args, kwargs = gen_args_kwargs(args=args,
                                           kwargs=kwargs,
                                           mapping=arg_mapping_container[0])
            return wrapped(*args, **kwargs)

        return fast_inject

    def prepare(self, func, use_arg_name=False, mapping=None, args=None,
                kwargs=None):
        """
        Creates a partial function with the injected arguments.

        It should be used whenever a function is called repeatedly.

        Args:
            func (callable): Callable for which the argument should be
                injected.
            use_arg_name (bool, optional): Whether the arguments name
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
        new_args, new_kwargs = self._generate_args_kwargs(
            args=args or tuple(),
            kwargs=kwargs or dict(),
            mapping=self._generate_arguments_mapping(
                func=func,
                mapping=mapping or dict(),
                use_arg_name=use_arg_name
            )
        )

        return functools.partial(func, *new_args, **new_kwargs)

    def _generate_args_kwargs(self, args, kwargs, mapping):
        kwargs = kwargs.copy()
        container = self._container

        for arg_name, dependency_id in islice(mapping.items(), len(args),
                                              None):
            if dependency_id is not _EMPTY_DEPENDENCY \
                    and arg_name not in kwargs:
                try:
                    kwargs[arg_name] = container[dependency_id]
                except DependencyNotFoundError:
                    pass

        return args, kwargs

    def _generate_arguments_mapping(self, func, use_arg_name, mapping):
        arguments_name = self._get_arguments_name(func=func)
        arguments_mapping = OrderedDict(zip(
            arguments_name,
            [_EMPTY_DEPENDENCY] * len(arguments_name)
        ))

        arguments_mapping.update(getattr(func, '__annotations__', {}))
        arguments_mapping.pop('return', None)

        for arg_name, dependency_id in mapping.items():
            if arg_name in arguments_mapping:
                arguments_mapping[arg_name] = dependency_id

        for arg_name, dependency_id in arguments_mapping.items():
            if dependency_id is _EMPTY_DEPENDENCY \
                    or dependency_id not in self._container:
                arguments_mapping[arg_name] = (arg_name
                                               if use_arg_name else
                                               _EMPTY_DEPENDENCY)

        return arguments_mapping

    if PY3:
        @classmethod
        def _get_arguments_name(cls, func):
            return tuple(inspect.signature(func).parameters.keys())
    else:
        @classmethod
        def _get_arguments_name(cls, func):
            try:
                return tuple(inspect.getargspec(func).args)
            except TypeError:  # builtin methods or object.__init__
                return tuple()
