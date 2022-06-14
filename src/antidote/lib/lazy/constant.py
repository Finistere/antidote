from __future__ import annotations

from typing import Any, Callable, overload, Type, TypeVar

from typing_extensions import Concatenate, ParamSpec, Protocol, TypeGuard

from ..._internal import API, Default
from ...core import Catalog, Dependency, TypeHintsLocals, world

__all__ = [
    "Const",
    "ConstFactory",
    "ConstantFactoryMethod",
    "ConstantFactoryFunction",
    "is_const_factory",
    "ConstFactoryDecorator",
]

T = TypeVar("T")
P = ParamSpec("P")
Out = TypeVar("Out", covariant=True)


@API.public
class ConstantFactoryFunction(Protocol[P, Out]):
    # Have to copy-paste LazyFunction for Mypy... error: ParamSpec "P" is unbound
    @property
    def __wrapped__(self) -> Callable[P, Out]:
        ...

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Dependency[Out]:
        ...


@API.public
class ConstantFactoryMethod(Protocol[P, Out]):
    # Have to copy-paste LazyFunction for Mypy... error: ParamSpec "P" is unbound
    @property
    def __wrapped__(self) -> Callable[Concatenate[Any, P], Out]:
        ...

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Dependency[Out]:
        ...

    def __get__(self, instance: object, owner: type) -> ConstantFactoryMethod[P, Out]:
        ...


@API.public
class ConstFactory(Protocol):
    @overload
    def __call__(
        self,
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> ConstFactoryDecorator:
        ...

    @overload
    def __call__(
        self,
        __func: staticmethod[Callable[P, T]],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> staticmethod[ConstantFactoryFunction[P, T]]:
        ...

    @overload
    def __call__(
        self,
        __func: Callable[P, T],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> ConstantFactoryFunction[P, T]:
        ...

    def __call__(
        self,
        __func: object = None,
        *,
        inject: None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog = world,
    ) -> object:
        ...

    @overload
    def method(
        self,
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> Callable[[Callable[Concatenate[Any, P], T]], ConstantFactoryMethod[P, T]]:
        ...

    @overload
    def method(
        self,
        __func: Callable[Concatenate[Any, P], T],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> ConstantFactoryMethod[P, T]:
        ...

    def method(
        self,
        __func: object = None,
        *,
        inject: None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog = world,
    ) -> object:
        ...


@API.public
class Const(Protocol):
    """
    This class itself shouldn't be used directly, rely on the singleton :py:obj:`.const` instead.

    Used to declare constants, typically configuration which may be retrieved from the
    environment, a file, etc... The simplest case are static constants:

    .. doctest:: lib_lazy_constant_const

        >>> from antidote import const, world, inject
        >>> class Conf:
        ...     HOST = const('localhost')
        ...     PORT = const(80)
        >>> @inject
        ... def f(host: str = Conf.HOST) -> str:
        ...     return host
        >>> f()
        'localhost'
        >>> world.get[str](Conf.HOST)
        'localhost'

    Now, :py:obj:`.const` really shines when you need to change how the constant values are
    retrieved as you don't need to change your API! You can build your own logic with
    :py:meth:`.Const.factory` or use the provided :py:obj:`.Const.env` to retrieve environment
    variables.

    When a constant is accessed through its class like :code:`Conf.HOST` it always returns a
    dependency to be used with :py:obj:`.inject` or :py:mod:`.world`. When accessed through the
    instance it'll return the actual value. This make it a lot easier to test custom constants.

    .. doctest:: lib_lazy_constant_const

        >>> Conf.HOST
        Constant...
        >>> Conf().HOST
        'localhost'

    """

    @property
    def factory(self) -> ConstFactory:
        ...

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
        cast: Type[T],
        catalog: Catalog = ...,
    ) -> Dependency[T]:
        ...

    @overload
    def env(
        self,
        __var_name: str = ...,
        *,
        default: T,
        cast: Type[T],
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
        cast: type | None = None,
        catalog: Catalog = world,
    ) -> object:
        """
        Declares a constant loaded from a environment variables. By default, it
        relies on the constant name to infer the environement variable, but it can be explicitely
        provided.

        For :py:class:`int`, :py:class:`str`, :py:class:`float` and all :py:class:`~enum.Enum`, if
        the type is explicitly specified, :code:`env[int](...)`, the environment value will be
        forcefully converted to it.

        .. doctest:: lib_lazy_constant_const_env

            >>> from antidote import const, world, inject
            >>> class Conf:
            ...     # Specifying explicitly the environment variable name
            ...     HOST = const.env('HOSTNAME')
            ...     # Here the attribute name is used and the value will be converted to an int.
            ...     PORT = const.env[int]()
            ...     UNKNOWN = const.env(default='not found!')
            >>> import os
            >>> os.environ['HOSTNAME'] = 'localhost'
            >>> os.environ['PORT'] = '80'
            >>> @inject
            ... def f(port: int = Conf.PORT) -> int:
            ...     return port
            >>> f()
            80
            >>> world.get[str](Conf.HOST)
            'localhost'
            >>> world.get[str](Conf.UNKNOWN)
            'not found!'
            >>> Conf().HOST
            'localhost'

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

            >>> from antidote import const
            >>> class StaticConf:
            ...     HOST = const('localhost')

        Args:
            __value: Value of the constant.

        Returns:
            Constant with a static value.
        """
        ...


@API.public
def is_const_factory(__obj: object) -> TypeGuard[Callable[..., Dependency[Any]]]:
    from ._constant import ConstFactoryWrapper

    return isinstance(__obj, ConstFactoryWrapper)


# Used for typing purposes, the protocol itself is not part of the public API.
@API.private
class ConstFactoryDecorator(Protocol):
    @overload
    def __call__(
        self, __func: staticmethod[Callable[P, T]]
    ) -> staticmethod[ConstantFactoryFunction[P, T]]:
        ...

    @overload
    def __call__(self, __func: Callable[P, T]) -> ConstantFactoryFunction[P, T]:
        ...

    def __call__(self, __func: object) -> object:
        ...
