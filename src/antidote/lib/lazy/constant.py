from __future__ import annotations

from typing import Any, Optional, overload, Type, TypeVar, Union

from typing_extensions import Protocol

from ..._internal import API
from ..._internal.utils import Default
from ...core.annotations import HiddenDependency

__all__ = [
    "Const",
    "Constant",
    "ConstantFactory",
    "TypedConstantFactory",
    "ConstantValueProviderFunction",
    "ConstantValueProviderMethod",
    "ConstantValueProvider",
    "ConstantValueConverter",
    "ConstantValueConverterMethod",
]

T = TypeVar("T")
A = TypeVar("A")
Arg = TypeVar("Arg", contravariant=True)
Value = TypeVar("Value")
ValueCo = TypeVar("ValueCo", covariant=True)
ValueCt = TypeVar("ValueCt", contravariant=True)


@API.public
class Constant(Protocol[ValueCo]):
    """
    All constants are actually descriptors following this API. The real value of the constant
    is returned when accessing from the instance and a dependency is returned when access it from
    the class. However, for convenience, we lie in the static typing specifying that the real
    value is always returned making it easier to use with :py:func:`.inject`.
    """

    @overload
    def __get__(self, instance: None, owner: type) -> HiddenDependency[ValueCo]:
        ...

    @overload
    def __get__(self, instance: object, owner: type) -> ValueCo:
        ...

    def __get__(self, instance: Optional[object], owner: type) -> ValueCo:
        ...


@API.public
class TypedConstantFactory(Protocol[Arg, Value]):
    def __call__(
        self,
        __arg: Optional[Arg] = None,
        *,
        default: Union[Value, Default] = Default.sentinel,
    ) -> Constant[Value]:
        """
        Creates a new constant.

        Args:
            __arg: **/positional-only/** Argument given to the underlying factory if any.
            default: Default value used if the factory raised a :py:exc:`LookUpError`.

        Returns:
            A :py:class:`.Constant` descriptor.
        """
        ...


@API.public
class ConstantFactory(TypedConstantFactory[Arg, Value], Protocol[Arg, Value]):
    def __getitem__(self, __type: Type[T]) -> TypedConstantFactory[Arg, T]:
        """
        Used to enforce a specific type for the constant value. It may also be used forcefully
        convert the raw constant value when specified with :code:`convert` argument of
        :py:meth:`.Const.factory`
        """
        ...


@API.public
class ConstantValueProviderFunction(Protocol[Arg, ValueCo]):
    """
    Expected API for a factory function.
    """

    def __call__(self, name: str, arg: Optional[Arg]) -> ValueCo:
        """
        Args:
            name: Name of the constant
            arg: Argument given to :code:`const()` if any or :py:obj:`None`
        """
        ...


@API.public
class ConstantValueProviderMethod(Protocol[Arg, ValueCo]):
    """
    Expected API for a factory method.
    """

    def __call__(_, self: Any, name: str, arg: Optional[Arg]) -> ValueCo:
        """
        Args:
            self:
            name: Name of the constant
            arg: Argument given to :code:`const()` if any or :py:obj:`None`
        """
        ...


@API.public
class ConstantValueConverter(Protocol[ValueCt]):
    def __call__(self, value: ValueCt, tpe: Type[T]) -> T:
        ...


@API.public
class ConstantValueConverterMethod(Protocol[ValueCt]):
    def __call__(_, self: Any, value: ValueCt, tpe: Type[T]) -> T:
        ...


@API.public
class ConstantValueProvider(Protocol[Arg, Value]):
    """
    Wrapper protocol of a wrapped :py:meth:`.Const.factory` function / method. The underlying
    function can be accessed directly through
    :py:attr:`~.WrappedConstantFactoryFunction.__wrapped__`. Calling the function has exactly the
    same behavior. Only a :py:attr:`~.ConstantValueProvider.const` attribute is added to
    build constants.

    .. doctest:: lib_lazy_constant_wrapper

        >>> from typing import Optional
        >>> from antidote import const
        >>> @const.provider
        ... def f(name: str, arg: Optional[object], tpe: Optional[type]) -> object:
        ...     return name
        >>> f("test", arg=None, tpe=None)
        'test'

    See :py:meth:`.Const.factory` for usage instructions.
    """

    def __call__(self, name: str, *, arg: Optional[Arg]) -> Value:
        """
        Args:
            name: Name of the constant
            arg: Argument given to :code:`const(arg)` if any.
        """
        ...

    @property
    def __wrapped__(self) -> object:
        """
        Actual function wrapped by :py:meth:`.Const.factory`.
        """
        ...

    @property
    def const(self) -> ConstantFactory[Arg, Value]:
        ...

    @API.experimental
    def converter(
        self, __func: ConstantValueConverter[Value] | ConstantValueConverterMethod[Value]
    ) -> ConstantValueConverter[Value]:
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
    def env(self) -> ConstantFactory[str, str]:
        """
        Declares a constant loaded from a environment variables. By default it
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
        __value: Optional[Value] = None,
        *,
        default: API.Deprecated[Union[Value, Default]] = Default.sentinel,
    ) -> Constant[Value]:
        """
        Create a static constant with a pre-defined value. :py:class:`.Constants` modifies this
        behavior, but it's deprecated.

        .. doctest:: lib_lazy_constant_const

            >>> from antidote import const
            >>> class StaticConf:
            ...     HOST = const('localhost')

        Args:
            __value: Value of the constant.
            default:
                .. deprecated:: 1.4

                    Only present for backwards compatibility for :py:class:`.Constants`.

        Returns:
            Constant with a static value.
        """
        ...

    # Present for backwards compatibility
    @API.deprecated
    def __getitem__(self, __type: Type[T]) -> TypedConstantFactory[object, T]:
        """
        .. deprecated:: 1.4

            Only present for backwards compatibility for :py:class:`.Constants`.

        """
        ...

    def provider(
        self, __func: ConstantValueProviderFunction[Arg, T] | ConstantValueProviderMethod[Arg, T]
    ) -> ConstantValueProvider[Arg, T]:
        """
        Creates a custom constant statefull or stateless provider. The wrapped function or method
        must have at least two arguments:

        - :code:`name`: name of the constant.
        - :code:`arg:`: optional argument given to :code:`const(arg)`. Defaults to :py:obj:`None`
          if not specified with :py:obj:`.const`.

        The returned wrapper is a :py:class:`.ConstantValueProvider` which keeps the same
        behavior for the function and adds an :py:attr:`~.ConstantValueProvider.const`
        attribute and a :py:meth:`~.ConstantValueProvider.converter` method.

        Type conversion can be forced with :py:meth:`~.ConstantValueProvider.converter`.
        The default value is returned upon a :py:exc:`LookUpError`. Hereafter is a re-implementation
        of :py:attr:`.Const.env` using a stateless provider:

        .. doctest:: lib_lazy_constant_const_factory

            >>> from typing import Optional, TypeVar, Type
            >>> import os
            >>> from antidote import const, world, inject
            >>> T = TypeVar('T')
            >>> @const.provider
            ... def env(name: str, arg: Optional[str]) -> str:
            ...     return os.environ[arg or name]
            >>> @env.converter
            ... def convert(value: object, tpe: Type[T]) -> T:
            ...     if issubclass(tpe, (str, int, float)):
            ...         return tpe(value)
            ...     raise TypeError(f"Unsupported {tpe}")
            >>> class Conf:
            ...     HOST = env.const('HOSTNAME')
            ...     PORT = env.const[int]()
            ...     UNKNOWN = env.const(default='not found!')
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

        If you need to mange some state, you can keep it inside :code:`Conf` and use a method as a
        factory. The class MUST be defined as an singleton with :py:func:`.injectable`:

        .. doctest:: lib_lazy_constant_const_factory

            >>> from antidote import injectable
            >>> @injectable
            ... class Conf:
            ...     def __init__(self):
            ...         # loaded from a file for example:
            ...         self.__data = {'port': 80, 'host': 'localhost'}
            ...
            ...     @const.provider
            ...     def get(self, name: str, arg: Optional[str]) -> object:
            ...         return self.__data[arg]
            ...
            ...     HOST = get.const('host')
            ...     PORT = get.const[int]('port')

        Args:
            __func: **/positional-only/** Provider function to use when creating the constant value.
                :py:obj:`.inject` will be applied on it.

        Returns:
            The wrapped provider with an additional :py:attr:`~.ConstantValueProvider.const`
            attribute which can be used to create constants with the same API as :py:obj:`.const`.
        """
        ...
