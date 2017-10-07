import inspect
from itertools import islice

from ._compat import PY3
from .exceptions import *


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
        new_args, new_kwargs = self._inject_services(
            cls.__init__,
            skip_self=True,
            inject_by_name=inject_by_name,
            mapping=mapping or dict(),
            args=args or tuple(),
            kwargs=kwargs or dict()
        )

        return cls(*new_args, **new_kwargs)

    def call(self, func, inject_by_name=False, mapping=None, args=None,
             kwargs=None):
        """
        Injects the missing arguments and calls the function.
        """
        new_args, new_kwargs = self._inject_services(
            func,
            skip_self=False,
            inject_by_name=inject_by_name,
            mapping=mapping or dict(),
            args=args or tuple(),
            kwargs=kwargs or dict()
        )

        return func(*new_args, **new_kwargs)

    if PY3:
        def _inject_services(self, f, skip_self, inject_by_name, mapping, args,
                             kwargs):
            len_args = len(args) + (1 if skip_self else 0)
            signature = inspect.signature(f)

            kwargs = kwargs.copy()
            for name, parameter in islice(signature.parameters.items(),
                                          len_args, None):
                try:
                    service_name = mapping[name]
                except KeyError:
                    service_name = parameter.annotation
                    if service_name is parameter.empty:
                        service_name = inject_by_name and name

                if name not in kwargs and service_name:
                    try:
                        kwargs[name] = self._container[service_name]
                    except UnregisteredServiceError:
                        pass

            bound_arguments = signature.bind_partial(*args, **kwargs)

            return bound_arguments.args, bound_arguments.kwargs
    else:
        def _inject_services(self, f, skip_self, inject_by_name, mapping, args,
                             kwargs):
            len_args = len(args) + (1 if skip_self else 0)
            try:
                arguments = inspect.getargspec(f).args
            except TypeError:
                pass
            else:
                kwargs = kwargs.copy()
                for name in islice(arguments, len_args, None):
                    if name not in kwargs:
                        try:
                            kwargs[name] = self._container[mapping[name]]
                        except (KeyError, UnregisteredServiceError):
                            if inject_by_name:
                                try:
                                    kwargs[name] = self._container[name]
                                except UnregisteredServiceError:
                                    pass

            return args, kwargs
