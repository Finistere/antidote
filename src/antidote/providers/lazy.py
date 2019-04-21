from typing import Callable, Optional, Union, Tuple, Dict

from .._internal.utils import SlotsReprMixin
from ..core import DependencyInstance, DependencyProvider


class LazyCall(SlotsReprMixin):
    __slots__ = ('func', 'args', 'kwargs', 'singleton')

    def __init__(self, func: Callable, singleton=True):
        self.singleton = singleton
        self.func = func
        self.args = ()  # type: Tuple
        self.kwargs = {}  # type: Dict

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return self


class LazyMethodCall(SlotsReprMixin):
    __slots__ = ('_method', '_args', '_kwargs')

    def __init__(self, method: Callable):
        self._method = method
        self._args = ()  # type: Tuple
        self._kwargs = {}  # type: Dict

    def __call__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        return self

    def __get__(self, instance, owner):
        if instance is None:
            return owner.__dict__.get(self, LazyMethodCallDependency(self, owner))
        return self._method(instance, *self._args, **self._kwargs)


class LazyMethodCallDependency(SlotsReprMixin):
    __slots__ = ('lazy_call', 'owner')

    def __init__(self, lazy_call, owner):
        self.lazy_call = lazy_call
        self.owner = owner


class LazyCallProvider(DependencyProvider):
    bound_dependency_types = (LazyMethodCallDependency, LazyCall)

    def provide(self,
                dependency: Union[LazyMethodCallDependency, LazyCall]
                ) -> Optional[DependencyInstance]:
        if isinstance(dependency, LazyMethodCallDependency):
            return DependencyInstance(
                dependency.lazy_call.__get__(
                    self._container.provide(dependency.owner),
                    dependency.owner
                ),
                singleton=True
            )
        elif isinstance(dependency, LazyCall):
            return DependencyInstance(
                dependency.func(*dependency.args, **dependency.kwargs),
                singleton=dependency.singleton
            )
