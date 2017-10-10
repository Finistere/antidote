import functools
import inspect
from collections import OrderedDict
from itertools import islice

from ._compat import PY3
from .exceptions import *

_sentinel = object()


class Builder:
    """
    Injects the services from a container before building an object or calling
    a function.
    """
    def __init__(self, container):
        self._container = container

    def build(self, cls, inject_by_name=False, mapping=None, args=None,
              kwargs=None):
        """
        Injects the parameters of __init__() and builds an object of
        class 'cls'.
        """
        arg_mapping = self.generate_arguments_mapping(
            cls.__init__,
            inject_by_name=inject_by_name,
            mapping=mapping
        )
        new_args, new_kwargs = self.generate_injected_args_kwargs(
            dict(islice(arg_mapping.items(), 1, None)),  # skip self
            args=args or tuple(),
            kwargs=kwargs or dict()
        )

        return cls(*new_args, **new_kwargs)

    def call(self, func, inject_by_name=False, mapping=None, args=None,
             kwargs=None):
        """
        Injects the missing arguments and calls the function.
        """
        new_args, new_kwargs = self.generate_injected_args_kwargs(
            self.generate_arguments_mapping(func,
                                            inject_by_name=inject_by_name,
                                            mapping=mapping),
            args=args or tuple(),
            kwargs=kwargs or dict()
        )

        return func(*new_args, **new_kwargs)

    def prepare(self, func, inject_by_name=False, mapping=None, args=None,
                kwargs=None):
        """
        Injects the missing arguments and calls the function.
        """
        new_args, new_kwargs = self.generate_injected_args_kwargs(
            self.generate_arguments_mapping(func,
                                            inject_by_name=inject_by_name,
                                            mapping=mapping),
            args=args or tuple(),
            kwargs=kwargs or dict()
        )

        return functools.partial(func, *new_args, **new_kwargs)

    def generate_injected_args_kwargs(self, arguments_mapping, args, kwargs):
        """
        Injects the services into the arguments based on the arguments_mapping.
        """
        kwargs = kwargs.copy()
        for name, service_name in islice(arguments_mapping.items(),
                                         len(args), None):
            if name not in kwargs and service_name is not _sentinel:
                try:
                    kwargs[name] = self._container[service_name]
                except UnregisteredServiceError:
                    pass

        return args, kwargs

    if PY3:
        @classmethod
        def generate_arguments_mapping(cls, func, inject_by_name,
                                       mapping=None):
            """
            Generate the argument mapping, which can then be cached to
            diminish the service injection overhead.
            """
            mapping = mapping or dict()
            arguments_mapping = OrderedDict()
            for name, parameter in inspect.signature(func).parameters.items():
                try:
                    arguments_mapping[name] = mapping[name]
                except KeyError:
                    if parameter.annotation is parameter.empty:
                        if inject_by_name:
                            arguments_mapping[name] = name
                        else:
                            arguments_mapping[name] = _sentinel
                    else:
                        arguments_mapping[name] = parameter.annotation

            return arguments_mapping
    else:
        @classmethod
        def generate_arguments_mapping(cls, func, inject_by_name,
                                       mapping=None):
            """
            Generate the argument mapping, which can then be cached to
            diminish the service injection overhead.
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
                        if inject_by_name:
                            arguments_mapping[name] = name
                        else:
                            arguments_mapping[name] = _sentinel

            return arguments_mapping
