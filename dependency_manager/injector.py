import bisect
import functools
import inspect
from abc import ABCMeta, abstractmethod
from collections import OrderedDict
from itertools import islice

import wrapt
from future.utils import with_metaclass

from ._compat import PY3
from .exceptions import *

_sentinel = object()
_STATIC_INJECTION = object()
_DYNAMIC_INJECTION = object()


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
        self._hooks = SimpleSortedCollection()

    def add_injection_hook(self, hook, priority=None):
        """
        Add an InjectionHook for dynamic dependency generation.

        Args:
            hook (:py:class:`.InjectionHook`): Injection hook.
            priority (int, optional): Overrides the hooks priority.

        """
        self._hooks.add(
            key=priority if priority is not None else hook.priority,
            value=hook
        )

    def inject(self, mapping=None, use_arg_name=False):
        """Inject the dependency into the function.

        Args:
            mapping (dict, optional): Custom mapping of the arguments name
                to their respective dependency id. Overrides annotations.
                Defaults to None.
            use_arg_name (bool, optional): Whether the arguments name
                should be used to search for a dependency when no mapping,
                nor annotation is found. Defaults to False.

        Returns:
            callable: The injected function.

        """
        gen_args_kwargs = self._generate_injected_args_kwargs

        @wrapt.decorator
        def fast_inject(wrapped, instance, args, kwargs):
            try:
                arg_mapping = fast_inject.arg_mapping
            except AttributeError:
                arg_mapping = self._generate_arguments_mapping(
                    wrapped=wrapped,
                    instance=instance,
                    use_arg_name=use_arg_name,
                    mapping=mapping,
                )
                fast_inject.arg_mapping = arg_mapping

            args, kwargs = gen_args_kwargs(wrapped=wrapped,
                                           instance=instance,
                                           args=args,
                                           kwargs=kwargs,
                                           arguments_mapping=arg_mapping)
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
        new_args, new_kwargs = self._generate_injected_args_kwargs(
            wrapped=func,
            instance=None,
            args=args or tuple(),
            kwargs=kwargs or dict(),
            arguments_mapping=self._generate_arguments_mapping(
                wrapped=func,
                instance=None,
                use_arg_name=use_arg_name,
                mapping=mapping
            ),
        )

        return functools.partial(func, *new_args, **new_kwargs)

    def _generate_injected_args_kwargs(self, wrapped, instance, args, kwargs,
                                       arguments_mapping):
        """
        Injects the dependencies into the arguments based on the
        arguments_mapping and the arguments passed on by the :py:mod:`wrapt`
        decorator.

        Args:
            wrapped (callable): The wrapped function for which the dependencies
                are injected.
            instance (object): The object to which the wrapped function was
                bound when it was called.
            args (iterable): Positional arguments which override any injection.
            kwargs (dict): Keyword arguments which override any injection.
            arguments_mapping (:py:obj:`OrderedDict`): Mapping of the arguments
                to their dependency. If there is none, _sentinel must be used.

        Returns:
            tuple: New Positional arguments and Keyword arguments.

        """
        kwargs = kwargs.copy()
        container = self._container

        for arg_name, (injection_type, injection_args) in islice(
                arguments_mapping.items(), len(args), None
                ):
            if injection_type is not None and arg_name not in kwargs:
                try:
                    if injection_type is _STATIC_INJECTION:
                        kwargs[arg_name] = container[injection_args]
                    elif injection_type is _DYNAMIC_INJECTION:
                        dependency_provider, dependency_id = injection_args
                        kwargs[arg_name] = dependency_provider(
                            wrapped=wrapped,
                            instance=instance,
                            container=container,
                            dependency_id=dependency_id
                        )
                except DependencyNotFoundError:
                    pass

        return args, kwargs

    if PY3:
        def _generate_arguments_mapping(self, wrapped, instance, use_arg_name,
                                        mapping):
            """
            Generate the argument mapping, which can then be cached to
            diminish the service injection overhead.

            Args:
                wrapped (callable): Callable for which the argument mapping will
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

            for name, parameter in inspect.signature(wrapped).parameters.items():
                dependency_id = _sentinel
                try:
                    dependency_id = mapping[name]
                except KeyError:
                    if parameter.annotation is not parameter.empty:
                        dependency_id = parameter.annotation
                    elif use_arg_name:
                        dependency_id = name

                if dependency_id is not _sentinel:
                    for hook in self._hooks:
                        if hook.match(wrapped=wrapped, instance=instance,
                                      dependency_id=dependency_id):
                            arguments_mapping[name] = (
                                _DYNAMIC_INJECTION,
                                (hook.provide, dependency_id)
                            )
                            break
                    else:
                        arguments_mapping[name] = (_STATIC_INJECTION,
                                                   dependency_id)

            return arguments_mapping
    else:
        def _generate_arguments_mapping(self, wrapped, instance, use_arg_name,
                                        mapping):
            mapping = mapping or dict()
            arguments_mapping = OrderedDict()

            try:
                argspec = inspect.getargspec(wrapped)
            except TypeError:  # builtin methods or object.__init__
                return arguments_mapping

            for name in argspec.args:
                dependency_id = _sentinel
                try:
                    dependency_id = mapping[name]
                except KeyError:
                    if use_arg_name:
                        dependency_id = name

                if dependency_id is not _sentinel:
                    for hook in self._hooks:
                        if hook.match(wrapped=wrapped, instance=instance,
                                      dependency_id=dependency_id):
                            arguments_mapping[name] = (
                                _DYNAMIC_INJECTION,
                                (hook.provide, dependency_id)
                            )
                            break
                    else:
                        arguments_mapping[name] = (_STATIC_INJECTION,
                                                   dependency_id)

            return arguments_mapping


class InjectionHook(with_metaclass(ABCMeta)):
    """
    Allows to dynamically provide the dependency to a set of functions.
    """
    priority = 0

    @abstractmethod
    def match(self, wrapped, instance, dependency_id):
        """Whether th

        Args:
            wrapped (callable): The wrapped function for which the dependencies
                are injected.
            instance (object): The object to which the wrapped function was
                bound when it was called.
            dependency_id (object): Id of the dependency.

        Returns:
            bool: Whether this hook should be used to provide the dependency.
        """

    @abstractmethod
    def provide(self, container, wrapped, instance, dependency_id):
        """Provide the dependency.

        If the dependency cannot be provided,
        :py:exc:`.DependencyNotFoundError` should be raised.

        Args:
            wrapped (callable): The wrapped function for which the dependencies
                are injected.
            instance (object): The object to which the wrapped function was
                bound when it was called.
            dependency_id (object): Id of the dependency.
            container (:py:class:`.DependencyContainer`): The
                container used by the :py:class:`.DependencyInjector`.

        Returns:
            The dependency
        """


class SimpleSortedCollection(object):
    def __init__(self):
        self._values = []
        self._keys = []

    def add(self, key, value):
        i = bisect.bisect(self._keys, key)
        self._keys.insert(i, key)
        self._values.insert(i, value)

    def __iter__(self):
        return iter(self._values)
