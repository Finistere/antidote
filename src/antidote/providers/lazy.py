from typing import Callable, Dict, Hashable, Optional, Tuple, Union

from .._internal.utils import SlotsReprMixin
from ..core import DependencyInstance, DependencyProvider


class LazyCall(SlotsReprMixin):
    """
    Dependency which is the result of the call of the given function with the
    given arguments.

    .. doctest::

        >>> from antidote import LazyCall, world
        >>> def f(x, y):
        ...     print("Computing {} + {}".format(x, y))
        ...     return x + y
        >>> A = LazyCall(f)(2, y=3)
        >>> world.get(A)
        Computing 2 + 3
        5
    """
    __slots__ = ('_func', '_args', '_kwargs', '_singleton')

    def __init__(self, func: Callable, singleton: bool = True):
        """
        Args:
            func: Function to lazily call, any arguments given by calling
                to the instance of :py:class:`~.LazyCall` will be passed on.
            singleton: Whether or not this is a singleton or not.
        """
        self._singleton = singleton
        self._func = func
        self._args = ()  # type: Tuple
        self._kwargs = {}  # type: Dict

    def __call__(self, *args, **kwargs):
        """
        All argument are passed on to the lazily called function.
        """
        self._args = args
        self._kwargs = kwargs
        return self


class LazyMethodCall(SlotsReprMixin):
    """
    Similar to :py:class:`~.LazyCall` but adapted to methods within a class
    definition. The class has to be a registered service, as the class
    instantiation itself is also lazy.

    .. doctest::

        >>> from antidote import LazyMethodCall, register, world
        >>> @register
        ... class Constants:
        ...     def get(self, x: str):
        ...         return len(x)
        ...     A = LazyMethodCall(get)('test')
        >>> Constants.A
        LazyMethodCallDependency(...)
        >>> world.get(Constants.A)
        4
        >>> Constants().A
        4

    :py:class:`~.LazyMethodCall` has two different behaviors:

    - if retrieved as a class attribute it returns a dependency which identifies
      the result for Antidote.
    - if retrieved as a instance attribute it returns the result for this
      instance. This makes testing a lot easier as it does not require Antidote.

    Check out :py:class:`~.helpers.conf.LazyConstantsMeta` for simple way
    to declare multiple constants.
    """
    __slots__ = ('_method_name', '_args', '_kwargs', '_singleton', '_key')

    def __init__(self, method: Union[Callable, str], singleton: bool = True):
        """

        Args:
            method: Method to be called or the name of it.
            singleton: Whether or not this is a singleton or not.
        """
        self._singleton = singleton
        # Retrieve the name of the method, as injection can be done after the class
        # creation which is typically the case with @register.
        self._method_name = method if isinstance(method, str) else method.__name__
        self._args = ()  # type: Tuple
        self._kwargs = {}  # type: Dict
        self._key = None

    def __call__(self, *args, **kwargs):
        """
        All argument are passed on to the lazily called function.
        """
        self._args = args
        self._kwargs = kwargs
        return self

    def __get__(self, instance, owner):
        if instance is None:
            if self._singleton:
                if self._key is None:
                    self._key = "{}_dependency".format(self._get_attribute_name(owner))
                    setattr(owner, self._key, LazyMethodCallDependency(self, owner))
                return getattr(owner, self._key)
            return LazyMethodCallDependency(self, owner)
        return getattr(instance, self._method_name)(*self._args, **self._kwargs)

    # The attribute is expected to be found in owner, as one should not call
    # directly __get__.
    def _get_attribute_name(self, owner):
        for k, v in owner.__dict__.items():  # pragma: no cover
            if v is self:
                return k


class LazyMethodCallDependency(SlotsReprMixin):
    __slots__ = ('lazy_method_call', 'owner')

    def __init__(self, lazy_method_call, owner):
        self.lazy_method_call = lazy_method_call
        self.owner = owner


class LazyCallProvider(DependencyProvider):
    bound_dependency_types = (LazyMethodCallDependency, LazyCall)

    def provide(self,
                dependency: Hashable
                ) -> Optional[DependencyInstance]:
        if isinstance(dependency, LazyMethodCallDependency):
            return DependencyInstance(
                dependency.lazy_method_call.__get__(
                    self._container.get(dependency.owner),
                    dependency.owner
                ),
                singleton=dependency.lazy_method_call._singleton
            )
        elif isinstance(dependency, LazyCall):
            return DependencyInstance(
                dependency._func(*dependency._args, **dependency._kwargs),
                singleton=dependency._singleton
            )
        return None
