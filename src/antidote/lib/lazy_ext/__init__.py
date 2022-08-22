from __future__ import annotations

from typing import Any, Callable, overload, Type

from typing_extensions import Concatenate, ParamSpec, Protocol

from ..._internal import API, Default
from ..._internal.typing import Out, T
from ...core import Catalog, Dependency, LifetimeType, TypeHintsLocals, world
from ._const import ConstImpl
from ._lazy import LazyImpl

__all__ = [
    "const",
    "lazy",
    "is_lazy",
    "Lazy",
    "Const",
    "antidote_lib_lazy",
    "LazyFunction",
    "LazyProperty",
    "LazyMethod",
    "LazyValue",
]

P = ParamSpec("P")

const: Const = ConstImpl()
lazy: Lazy = LazyImpl()


@API.public
def antidote_lib_lazy(catalog: Catalog) -> None:
    """
    Adds the necessary for the use of :py:obj:`.lazy` and :py:obj:`.const` into the specified
    catalog. The function is idempotent, and will not raise an error if it was already applied

    .. doctest:: lib_lazy_extension_include

        >>> from antidote import new_catalog, antidote_lib_lazy
        >>> # Include at catalog creation
        ... catalog = new_catalog(include=[antidote_lib_lazy])
        >>> # Or afterwards
        ... catalog.include(antidote_lib_lazy)

    """
    from ._provider import LazyProvider

    if LazyProvider not in catalog.providers:
        catalog.include(LazyProvider)


@API.public
def is_lazy(__obj: object) -> bool:
    """
    Returns :py:obj:`True` if the given object is a lazy function, method, value or property.

    .. doctest:: lib_lazy_is_lazy

        >>> from antidote import lazy, is_lazy
        >>> @lazy
        ... def f() -> None:
        ...     pass
        >>> is_lazy(f)
        True
        >>> is_lazy(object())
        False

    """
    from ._lazy import LazyWrapper

    return isinstance(__obj, LazyWrapper)


@API.public
class Const(Protocol):
    """
    Used to define constants, singleton dependencies. Use it through the singleton :py:obj:`.const`.
    """

    @overload
    def env(
        self,
        __var_name: str = ...,
        *,
        catalog: Catalog = ...,
    ) -> Dependency[str]:
        ...

    @overload
    def env(
        self,
        __var_name: str = ...,
        *,
        convert: Type[T] | Callable[[str], T],
        catalog: Catalog = ...,
    ) -> Dependency[T]:
        ...

    @overload
    def env(
        self,
        __var_name: str = ...,
        *,
        default: T,
        convert: Type[T] | Callable[[str], T],
        catalog: Catalog = ...,
    ) -> Dependency[T]:
        ...

    @overload
    def env(
        self,
        __var_name: str = ...,
        *,
        default: T,
        catalog: Catalog = ...,
    ) -> Dependency[T]:
        ...

    def env(
        self,
        __var_name: str | Default = Default.sentinel,
        *,
        default: object = Default.sentinel,
        convert: object | None = None,
        catalog: Catalog = world,
    ) -> object:
        """
        Declares a constant loaded from an environment variables. By default, it relies on the
        constant name to infer the environement variable, but it can be explicitely specified.

        .. doctest:: lib_lazy_constant_const_env

            >>> from antidote import const, world, inject
            >>> class Conf:
            ...     # Specifying explicitly the environment variable name
            ...     HOST = const.env('HOSTNAME')
            ...     # environment value will be converted to an int
            ...     PORT = const.env(convert=int)
            ...     UNKNOWN = const.env(default='not found!')
            >>> import os
            >>> os.environ['HOSTNAME'] = 'localhost'
            >>> os.environ['PORT'] = '80'
            >>> @inject
            ... def f(port: int = inject[Conf.PORT]) -> int:
            ...     return port
            >>> f()
            80
            >>> world[Conf.HOST]
            'localhost'
            >>> world[Conf.UNKNOWN]
            'not found!'

        .. note::

            Using a class as a namespace is not required, but it's convenient.

        """
        ...

    def __call__(
        self,
        __value: T,
        *,
        catalog: Catalog = world,
    ) -> Dependency[T]:
        """
        Create a static constant with a pre-defined value.

        .. doctest:: lib_lazy_constant_const

            >>> from antidote import const, world, inject
            >>> HOST = const('localhost')
            >>> @inject
            ... def f(host: str = inject[HOST]) -> str:
            ...     return host
            >>> f()
            'localhost'
            >>> world[HOST]
            'localhost'

        Args:
            __value: Value of the constant.
        """
        ...


@API.public
class Lazy(Protocol):
    """
    Used to define function calls as dependencies. Those can either be functions or methods and
    accept arguments or not. Use it through the singleton object :py:obj:`.lazy`.
    """

    @overload
    def __call__(
        self,
        *,
        lifetime: LifetimeType = ...,
        inject: None | Default = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> DecoratorLazyFunction:
        ...

    @overload
    def __call__(
        self,
        __func: staticmethod[Callable[P, T]],
        *,
        lifetime: LifetimeType = ...,
        inject: None | Default = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> staticmethod[LazyFunction[P, T]]:
        ...

    @overload
    def __call__(
        self,
        __func: Callable[P, T],
        *,
        lifetime: LifetimeType = ...,
        inject: None | Default = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> LazyFunction[P, T]:
        ...

    def __call__(
        self,
        __func: object = None,
        *,
        lifetime: LifetimeType = "singleton",
        inject: None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog = world,
    ) -> object:
        """
        Wraps a function defining a new dependency which is the function *call*.

        .. doctest:: lib_lazy_lazy

            >>> from antidote import inject, lazy, world
            >>> @lazy
            ... def template(name: str) -> str:
            ...     print("# Called main_template()")
            ...     return f"Template {name}"
            >>> main_template = template("main")
            >>> world[main_template]
            # Called main_template()
            'Template main'
            >>> @inject
            ... def f(t: str = inject[template("main")]) -> str:
            ...     return t
            >>> f()  # got the same instance as it's a singleton
            'Template main'
            >>> # the function itself is not a dependency
            ... template in world
            False

        By default, the dependency value has a :code:`singleton` :py:class:`.LifeTime`. Using the
        same arguments will return the same dependency value.

        .. doctest:: lib_lazy_lazy

            >>> world[template("main")] is world[template(name="main")]
            True

        .. warning::

            While it does positional and keyword arguments are properly handled it does *NOT* take
            into account default values. For this to work, arguments need to be hashable. It can
            only be avoided if the :py:class:`.LifeTime` is defined to be :code:`transient`.

        Args:
            __func: **/positional-only/** Function to wrap, which will be called lazily for
                dependencies.
            lifetime: Defines how long the dependency value will be cached. Defaults to
                :code:`'singleton'`, the function is called at most once per group of arguments.
            inject: Specifying :py:obj:`None` will prevent the use of py:obj:`.inject` on the
                function.
            type_hints_locals: Local variables to use for :py:func:`typing.get_type_hints`. They
                can be explicitly defined by passing a dictionary or automatically detected with
                :py:mod:`inspect` and frame manipulation by specifying :code:`'auto'`. Specifying
                :py:obj:`None` will deactivate the use of locals. The default behavior depends on the
                :py:data:`.config` value of :py:attr:`~.Config.auto_detect_type_hints_locals`. If
                :py:obj:`True` the default value is equivalent to specifying :code:`'auto'`,
                otherwise to :py:obj:`None`.
            catalog: Defines in which catalog the dependency should be registered. Defaults to
                :py:obj:`.world`.

        Returns:
            The function will be wrapped in a :py:class:`.LazyFunction`.
        """
        ...

    @overload
    def method(
        self,
        *,
        lifetime: LifetimeType = ...,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> Callable[[Callable[Concatenate[Any, P], T]], LazyMethod[P, T]]:
        ...

    @overload
    def method(
        self,
        __func: Callable[Concatenate[Any, P], T],
        *,
        lifetime: LifetimeType = ...,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> LazyMethod[P, T]:
        ...

    def method(
        self,
        __func: object = None,
        *,
        lifetime: LifetimeType = "transient",
        inject: None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog = world,
    ) -> object:
        """
        Wraps a method defining a new dependency which is the method *call*. Similar to
        :py:meth:`.Inject.method`, the first argument commonly named :code:`self` will be injected
        with the class instance.

        .. doctest:: lib_lazy_lazy_method

            >>> from antidote import injectable, lazy, world, inject
            >>> @injectable
            ... class Templates:
            ...     def __init__(self) -> None:
            ...         self.__templates = {'greeting': 'Hello {name}!', 'farewell': 'Bye {name}!'}
            ...
            ...     @lazy.method
            ...     def render(self, template: str, name: str) -> str:
            ...         return self.__templates[template].format(name=name)
            >>> world[Templates.render('greeting', name='John')]
            'Hello John!'
            >>> @inject
            ... def f(t: str = inject[Templates.render('greeting', name='Alice')]) -> str:
            ...     return t
            >>> f()
            'Hello Alice!'
            >>> # the function itself is not a dependency
            ... Templates.render in world
            False

        By default, the dependency value has a :code:`singleton` :py:class:`.LifeTime`. Using the
        same arguments will return the same dependency value.

        .. doctest:: lib_lazy_lazy_method

            >>> world[Templates.render('greeting', name='Alice')] is f()
            True

        .. warning::

            While it does positional and keyword arguments are properly handled it does *NOT* take
            into account default values. For this to work, arguments need to be hashable. It can
            only be avoided if the :py:class:`.LifeTime` is defined to be :code:`transient`.

        Args:
            __func: **/positional-only/** Function to wrap, which will be called lazily for
                dependencies.
            lifetime: Defines how long the dependency value will be cached. Defaults to
                :code:`'singleton'`, the method is called at most once per group of arguments.
            inject: Specifying :py:obj:`None` will prevent the use of py:obj:`.inject` on the
                function.
            type_hints_locals: Local variables to use for :py:func:`typing.get_type_hints`. They
                can be explicitly defined by passing a dictionary or automatically detected with
                :py:mod:`inspect` and frame manipulation by specifying :code:`'auto'`. Specifying
                :py:obj:`None` will deactivate the use of locals. The default behavior depends on the
                :py:data:`.config` value of :py:attr:`~.Config.auto_detect_type_hints_locals`. If
                :py:obj:`True` the default value is equivalent to specifying :code:`'auto'`,
                otherwise to :py:obj:`None`.
            catalog: Defines in which catalog the dependency should be registered. Defaults to
                :py:obj:`.world`.

        Returns:
            The function will be wrapped in a :py:class:`.LazyMethod`.
        """
        ...

    @overload
    def property(
        self,
        *,
        lifetime: LifetimeType = ...,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> Callable[[Callable[[Any], T]], LazyProperty[T]]:
        ...

    @overload
    def property(
        self,
        __func: Callable[[Any], T],
        *,
        lifetime: LifetimeType = ...,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> LazyProperty[T]:
        ...

    def property(
        self,
        __func: object = None,
        *,
        lifetime: LifetimeType = "transient",
        inject: None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog = world,
    ) -> object:
        """
        Wraps a function defining a new dependency which is the function *call* which does not
        accept any arguments. Similar to :py:meth:`.Inject.method`, the first argument commonly
        named :code:`self` will be injected with the class instance.

        .. doctest:: lib_lazy_lazy_property

            >>> from antidote import inject, lazy, world, injectable
            >>> @injectable
            ... class Status:
            ...     def __init__(self) -> None:
            ...         self.healthy_code = 200
            ...
            ...     @lazy.property
            ...     def code(self) -> int:
            ...         return self.healthy_code
            >>> world[Status.code]
            200
            >>> @inject
            ... def f(t: int = inject[Status.code]) -> int:
            ...     return t
            >>> f()
            200

        However, not accepting any argumnets does not mean that nothing can be injected:

        .. doctest:: lib_lazy_lazy_property

            >>> @injectable
            ... class HealthCheck:
            ...     @lazy.property
            ...     def current(self, status_code: int = inject[Status.code]) -> dict[str, object]:
            ...         return {'status': status_code}
            >>> world[HealthCheck.current]
            {'status': 200}

        By default, the dependency value has a :code:`singleton` :py:class:`.LifeTime`

        .. doctest:: lib_lazy_lazy_property

            >>> world[HealthCheck.current] is world[HealthCheck.current]
            True

        Args:
            __func: **/positional-only/** Function to wrap, which will be called lazily for
                dependencies.
            lifetime: Defines how long the dependency value will be cached. Defaults to
                :code:`'singleton'`, the method is called at most once.
            inject: Specifying :py:obj:`None` will prevent the use of py:obj:`.inject` on the
                function.
            type_hints_locals: Local variables to use for :py:func:`typing.get_type_hints`. They
                can be explicitly defined by passing a dictionary or automatically detected with
                :py:mod:`inspect` and frame manipulation by specifying :code:`'auto'`. Specifying
                :py:obj:`None` will deactivate the use of locals. The default behavior depends on the
                :py:data:`.config` value of :py:attr:`~.Config.auto_detect_type_hints_locals`. If
                :py:obj:`True` the default value is equivalent to specifying :code:`'auto'`,
                otherwise to :py:obj:`None`.
            catalog: Defines in which catalog the dependency should be registered. Defaults to
                :py:obj:`.world`.

        Returns:
            The function will be wrapped in a :py:class:`.LazyProperty`.
        """
        ...

    @overload
    def value(
        self,
        *,
        lifetime: LifetimeType = ...,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> Callable[[Callable[[], T] | staticmethod[Callable[[], T]]], LazyProperty[T]]:
        ...

    @overload
    def value(
        self,
        __func: Callable[[], T] | staticmethod[Callable[[], T]],
        *,
        lifetime: LifetimeType = ...,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> LazyValue[T]:
        ...

    def value(
        self,
        __func: object = None,
        *,
        lifetime: LifetimeType = "transient",
        inject: None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog = world,
    ) -> object:
        """
        Wraps a function defining a new dependency which is the function *call* which does not
        accept any arguments.

        .. doctest:: lib_lazy_lazy_value

            >>> from antidote import inject, lazy, world
            >>> @lazy.value
            ... def status() -> int:
            ...     return 200
            >>> world[status]
            200
            >>> @inject
            ... def f(t: int = inject[status]) -> int:
            ...     return t
            >>> f()
            200

        However, not accepting any argumnets does not mean that nothing can be injected:

        .. doctest:: lib_lazy_lazy_value

            >>> @lazy.value
            ... def healthcheck(status: int = inject[status]) -> dict[str, object]:
            ...     return {'status': status}
            >>> world[healthcheck]
            {'status': 200}

        By default, the dependency value has a :code:`singleton` :py:class:`.LifeTime`

        .. doctest:: lib_lazy_lazy_value

            >>> world[healthcheck] is world[healthcheck]
            True

        Args:
            __func: **/positional-only/** Function to wrap, which will be called lazily for
                dependencies.
            lifetime: Defines how long the dependency value will be cached. Defaults to
                :code:`'singleton'`, the function is called at most once.
            inject: Specifying :py:obj:`None` will prevent the use of py:obj:`.inject` on the
                function.
            type_hints_locals: Local variables to use for :py:func:`typing.get_type_hints`. They
                can be explicitly defined by passing a dictionary or automatically detected with
                :py:mod:`inspect` and frame manipulation by specifying :code:`'auto'`. Specifying
                :py:obj:`None` will deactivate the use of locals. The default behavior depends on the
                :py:data:`.config` value of :py:attr:`~.Config.auto_detect_type_hints_locals`. If
                :py:obj:`True` the default value is equivalent to specifying :code:`'auto'`,
                otherwise to :py:obj:`None`.
            catalog: Defines in which catalog the dependency should be registered. Defaults to
                :py:obj:`.world`.

        Returns:
            The function will be wrapped in a :py:class:`.LazyValue`.
        """
        ...


@API.public
class LazyFunction(Protocol[P, Out]):
    @property
    def __wrapped__(self) -> Callable[P, Out]:
        """
        Original wrapped function.
        """
        ...

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Dependency[Out]:
        ...


@API.public
class LazyMethod(Protocol[P, Out]):
    # Have to copy-paste LazyFunction for Mypy... error: ParamSpec "P" is unbound
    @property
    def __wrapped__(self) -> Callable[Concatenate[Any, P], Out]:
        """
        Original wrapped function.
        """
        ...

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Dependency[Out]:
        ...

    def __get__(self, instance: object, owner: type) -> LazyMethod[P, Out]:
        ...


@API.public
class LazyProperty(Dependency[Out], Protocol[Out]):
    @property
    def __wrapped__(self) -> Callable[[Any], Out]:
        """
        Original wrapped function.
        """
        ...


@API.public
class LazyValue(Dependency[Out], Protocol[Out]):
    @property
    def __wrapped__(self) -> Callable[[], Out]:
        """
        Original wrapped function.
        """
        ...


# Used for typing purposes, the protocol itself is not part of the public API.
@API.private
class DecoratorLazyFunction(Protocol):
    @overload
    def __call__(self, __func: staticmethod[Callable[P, T]]) -> staticmethod[LazyFunction[P, T]]:
        ...

    @overload
    def __call__(self, __func: Callable[P, T]) -> LazyFunction[P, T]:
        ...

    def __call__(self, __func: object) -> object:
        ...
