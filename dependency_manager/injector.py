import functools
import inspect
from collections import OrderedDict
from itertools import islice

from ._compat import PY3
from .exceptions import *

_sentinel = object()


class DependencyInjector:
    """
    Injects the dependencies from a container before building an object or
    calling a function.
    """
    def __init__(self, container):
        self._container = container

    def build(self, cls, use_arg_name=False, mapping=None, args=None,
              kwargs=None):
        """
        Instantiate an object with the dependencies of its class' __init__
        function injected.

        Args:
            cls (class): Class used.
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
            The result of the called function.

        """
        arg_mapping = self.generate_arguments_mapping(
            cls.__init__,
            use_arg_name=use_arg_name,
            mapping=mapping
        )
        new_args, new_kwargs = self.generate_injected_args_kwargs(
            OrderedDict(islice(arg_mapping.items(), 1, None)),  # skip self
            args=args or tuple(),
            kwargs=kwargs or dict()
        )

        return cls(*new_args, **new_kwargs)

    def call(self, func, use_arg_name=False, mapping=None, args=None,
             kwargs=None):
        """
        Calls a function after injecting its dependencies with the provided
        arguments.

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
            The result of the called function.

        """
        new_args, new_kwargs = self.generate_injected_args_kwargs(
            self.generate_arguments_mapping(func,
                                            use_arg_name=use_arg_name,
                                            mapping=mapping),
            args=args or tuple(),
            kwargs=kwargs or dict()
        )

        return func(*new_args, **new_kwargs)

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
        new_args, new_kwargs = self.generate_injected_args_kwargs(
            self.generate_arguments_mapping(func,
                                            use_arg_name=use_arg_name,
                                            mapping=mapping),
            args=args or tuple(),
            kwargs=kwargs or dict()
        )

        return functools.partial(func, *new_args, **new_kwargs)

    def generate_injected_args_kwargs(self, arguments_mapping, args, kwargs):
        """
        Injects the services into the arguments based on the arguments_mapping.

        Args:
            arguments_mapping (OrderedDict): Mapping of the arguments to their
                dependency. If there is none, _sentinel must be used.
            args (iterable): Positional arguments which override any injection.
            kwargs (dict): Keyword arguments which override any injection.

        Returns:
            tuple: New Positional arguments and Keyword arguments.

        """
        kwargs = kwargs.copy()
        for name, service_name in islice(arguments_mapping.items(),
                                         len(args), None):
            if service_name is not _sentinel and name not in kwargs:
                try:
                    kwargs[name] = self._container[service_name]
                except UnregisteredDependencyError:
                    pass

        return args, kwargs

    if PY3:
        @classmethod
        def generate_arguments_mapping(cls, func, use_arg_name=False,
                                       mapping=None):
            """
            Generate the argument mapping, which can then be cached to
            diminish the service injection overhead.

            Args:
                func (callable): Callable for which the argument mapping will
                    be generated.
                use_arg_name (bool, optional): Whether the arguments name
                    should be used to search for a dependency when no mapping,
                    nor annotation is found. Defaults to False.
                mapping (dict, optional): Custom mapping of the arguments name
                    to their respective dependency id. Overrides annotations.
                    Defaults to None.

            Returns:
                OrderedDict: Mapping of the arguments name to their matching
                    dependency id if one was found. If not _sentinel is used
                    instead.

            """
            mapping = mapping or dict()

            arguments_mapping = OrderedDict()
            for name, parameter in inspect.signature(func).parameters.items():
                try:
                    arguments_mapping[name] = mapping[name]
                except KeyError:
                    if parameter.annotation is parameter.empty:
                        if use_arg_name:
                            arguments_mapping[name] = name
                        else:
                            arguments_mapping[name] = _sentinel
                    else:
                        arguments_mapping[name] = parameter.annotation

            return arguments_mapping
    else:
        @classmethod
        def generate_arguments_mapping(cls, func, use_arg_name=False,
                                       mapping=None):
            """
            Generate the argument mapping, which can then be cached to
            diminish the service injection overhead.

            Args:
                func (callable): Callable for which the argument mapping will
                    be generated.
                use_arg_name (bool, optional): Whether the arguments name
                    should be used to search for a dependency when no mapping,
                    nor annotation is found. Defaults to False.
                mapping (dict, optional): Custom mapping of the arguments name
                    to their respective dependency id. Overrides annotations.
                    Defaults to None.

            Returns:
                OrderedDict: Mapping of the arguments name to their matching
                    dependency id if one was found. If not _sentinel is used
                    instead.

            """
            mapping = mapping or dict()

            arguments_mapping = OrderedDict()
            try:
                argspec = inspect.getargspec(func)
            except TypeError:  # builtin methods or object.__init__
                pass
            else:
                for name in argspec.args:
                    try:
                        arguments_mapping[name] = mapping[name]
                    except KeyError:
                        if use_arg_name:
                            arguments_mapping[name] = name
                        else:
                            arguments_mapping[name] = _sentinel

            return arguments_mapping
