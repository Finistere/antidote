from typing import Callable, Dict, Optional, Tuple, Union

from .._internal.utils import SlotsReprMixin
from ..core import DependencyInstance, DependencyProvider


class LazyCall(SlotsReprMixin):
    __slots__ = ('func', 'args', 'kwargs', 'singleton')

    def __init__(self, func: Callable, singleton: bool = True):
        self.singleton = singleton
        self.func = func
        self.args = ()  # type: Tuple
        self.kwargs = {}  # type: Dict

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return self


class LazyMethodCall(SlotsReprMixin):
    __slots__ = ('_method_name', '_args', '_kwargs', 'singleton')

    def __init__(self, method: Union[Callable, str], singleton: bool = True):
        self.singleton = singleton
        # Retrieve the name of the method, as injection can be done after the class
        # creation which is typically the case with @register.
        self._method_name = method if isinstance(method, str) else method.__name__
        self._args = ()  # type: Tuple
        self._kwargs = {}  # type: Dict

    def __call__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        return self

    def __get__(self, instance, owner):
        if instance is None:
            return owner.__dict__.get(self, LazyMethodCallDependency(self, owner))
        return getattr(instance, self._method_name)(*self._args, **self._kwargs)


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
                singleton=dependency.lazy_call.singleton
            )
        elif isinstance(dependency, LazyCall):
            return DependencyInstance(
                dependency.func(*dependency.args, **dependency.kwargs),
                singleton=dependency.singleton
            )
