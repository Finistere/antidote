import weakref
from typing import Callable, Optional

from ._compatibility.typing import final
from ._internal import API
from ._internal.utils import FinalImmutable, debug_repr, short_id
from ._lazy import (LazyCallWithArgsKwargs, LazyMethodCallDependency,
                    LazyMethodCallWithArgsKwargs)
from ._providers import Lazy
from .core import Container, DependencyDebug, DependencyValue, Scope
from .service import Service
from .utils import validated_scope


@API.public
@final
class LazyCall(FinalImmutable, Lazy):
    """
    Declares the result of a function call as a depdency.

    .. doctest:: lazy_func

        >>> from antidote import LazyCall, world
        >>> def f(x, y):
        ...     return x + y
        >>> Computation = LazyCall(f)(2, y=3)
        >>> world.get(Computation)
        5
        >>> user = 'John'
        >>> def hello():
        ...     return f"Hello {user}"
        >>> HelloUser = LazyCall(hello, singleton=False)
        >>> world.get(HelloUser)
        'Hello John'
        >>> user = "Adam"
        >>> world.get(HelloUser)
        'Hello Adam'

    """
    __slots__ = ('func', '_scope')
    func: Callable[..., object]
    _scope: Optional[Scope]

    def __init__(self,
                 func: Callable[..., object],
                 *,
                 singleton: bool = None,
                 scope: Optional[Scope] = Scope.sentinel()) -> None:
        """
        Args:
            func: Function to lazily call, any (keyword-)arguments given by the returned
                :py:class:`~.LazyCall` itself will be propagated.
            singleton: Whether the lazy dependency is a singleton or not. If yes,
                the function will be called at most once and the result re-used. Mutually
                exclusive with :code:`scope`. Defaults to :py:obj:`True`.
            scope: Scope of the dependency. Mutually exclusive with :code:`singleton`.
                The scope defines if and how long the returned dependency will be
                cached. See :py:class:`~.core.container.Scope`. Defaults to
                :py:meth:`~.core.container.Scope.singleton`.
        """
        if not callable(func):
            raise TypeError(f"func must be a callable, not {type(func)}")
        super().__init__(func, validated_scope(scope,
                                               singleton,
                                               default=Scope.singleton()))

    def __call__(self, *args: object, **kwargs: object) -> 'LazyCallWithArgsKwargs':
        """
        All argument are passed on to the lazily called function.
        """
        return LazyCallWithArgsKwargs(self.func, self._scope, args, kwargs)

    @API.private
    def __antidote_debug_repr__(self) -> str:
        s = f"Lazy: {debug_repr(self.func)}()"
        if self._scope is not None:
            s += f"  #{short_id(self)}"
        return s

    @API.private
    def debug_info(self) -> DependencyDebug:
        return DependencyDebug(self.__antidote_debug_repr__(),
                               scope=self._scope,
                               wired=[self.func])

    @API.private
    def provide(self, container: Container) -> DependencyValue:
        return DependencyValue(self.func(), scope=self._scope)


@API.public
@final
class LazyMethodCall(FinalImmutable):
    """
    Similar to :py:class:`~.LazyCall` but adapted to methods within a class definition.
    It can only be used with a :py:class:`.Service` subclass.

    :py:class:`~.LazyMethodCall` behaves in a similar way as constants in
    :py:class:`.Constants`. When accessed as class attributes, the dependency is returned.
    But on an instance, the actual method call result is returned.

    .. doctest:: lazy_method

        >>> from antidote import LazyMethodCall, Service, world
        >>> class Api(Service):
        ...     def __init__(self, host: str = 'localhost'):
        ...         self.host = host
        ...
        ...     def query(self, url: str = '/status'):
        ...         return f"requested {self.host}{url}"
        ...
        ...     status = LazyMethodCall(query, singleton=False)
        ...     conf = LazyMethodCall(query)('/conf')
        >>> world.get(Api.conf)
        'requested localhost/conf'
        >>> world.get(Api.status)
        'requested localhost/status'
        >>> # For ease of use, accessing the dependency through a instance will simply
        ... # call the method without passing through Antidote. Useful for tests typically
        ... Api(host='example.com').status
        'requested example.com/status'

    .. note::

        Consider using :py:class:`~.extension.constants.Constants` if you only declare
        constants.

    """
    __slots__ = ('_method_name', '_scope', '__cache_attr')
    _method_name: str
    _scope: Optional[Scope]
    __cache_attr: str

    def __init__(self,
                 method: Callable[..., object],
                 *,
                 singleton: bool = None,
                 scope: Scope = Scope.sentinel()) -> None:
        """
        Args:
            method: Method name or the method itself that must be called.
            singleton: Whether the lazy dependency is a singleton or not. If yes,
                the function will be called at most once and the result re-used. Mutually
                exclusive with :code:`scope`. Defaults to :py:obj:`True`.
            scope: Scope of the dependency. Mutually exclusive with :code:`singleton`.
                The scope defines if and how long the returned dependency will be
                cached. See :py:class:`~.core.container.Scope`. Defaults to
                :py:meth:`~.core.container.Scope.singleton`.
        """
        if not callable(method):
            raise TypeError("method must be a method or its name")
        super().__init__(
            method.__name__,
            validated_scope(scope, singleton, default=Scope.singleton()),
            f"__antidote_dependency_{hex(id(self))}"
        )

    def __call__(self, *args: object, **kwargs: object) -> 'LazyMethodCallWithArgsKwargs':
        """
        All argument are passed on to the lazily called method.
        """
        return LazyMethodCallWithArgsKwargs(self._method_name,
                                            self._scope,
                                            args,
                                            kwargs)

    def __str__(self) -> str:
        s = f"Lazy Method: {self._method_name}()"
        if self._scope is not None:
            s += f"  #{short_id(self)}"
        return s

    def __get__(self, instance: object, owner: type) -> object:
        if not issubclass(owner, Service):
            raise RuntimeError("LazyMethod can only be used on a Service subclass.")

        if instance is None:
            try:
                return getattr(owner, self.__cache_attr)
            except AttributeError:
                dependency = LazyMethodCallDependency(self, weakref.ref(owner))
                setattr(owner, self.__cache_attr, dependency)
                return dependency
        return getattr(instance, self._method_name)()
