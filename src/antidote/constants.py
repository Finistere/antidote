from __future__ import annotations

import collections.abc as c_abc
from typing import Any, ClassVar, FrozenSet, Iterable, Optional, Sequence, Union

from typing_extensions import final

from ._constants import ConstantsMeta
from ._internal import API
from ._internal.utils import Copy, FinalImmutable
from .core.wiring import Wiring, WithWiringMixin


@API.public
class Constants(metaclass=ConstantsMeta, abstract=True):
    """
    .. deprecated:: 1.4
        Deprecated in the sense that it's not necessary anymore. You can use :py:obj:`.const`
        without inheriting this class anymore.

    .. admonition:: MIGRATION

        For static constants, without a custom :code:`provide_const` you have nothing to do,
        just remove :py:class:`.Constants`. If you're retrieving the constants from environment
        variables consider using :py:attr:`~.ConstSingleton.env`. Otherwise you can rely on
        a const :py:meth:`~.ConstSingleton.factory`:

        .. doctest:: constants_migration

            >>> from typing import Optional
            >>> from antidote import const, injectable, world
            >>> @injectable
            ... class Config:
            ...     def __init__(self):
            ...         self._data = {'host': 'localhost', 'port': 80}
            ...
            ...     @const.provider
            ...     def provide(self, name: str, arg: Optional[str]) -> object:
            ...         return self._data[arg]
            ...
            ...     PORT = provide.const[int]('port')
            ...     HOST = provide.const[str]('host')
            >>> world.get[int](Config.PORT)
            80
            >>> world.get[str](Config.HOST)
            'localhost'


    Used to declare constants, typically configuration which may be retrieved from the
    environment, a file, etc...

    Constants are simply defined with :py:obj:`.const`:

    .. doctest:: constants

        >>> from antidote import Constants, const, world
        >>> class Config(Constants):
        ...     PORT = const(80)
        ...     HOST = const('localhost')
        >>> world.get[int](Config.PORT)
        80
        >>> world.get[str](Config.HOST)
        'localhost'
        >>> # Or directly from an instance, for testing typically:
        ... Config().PORT
        80

    :py:class:`.Constants` really shines when you need to change *how* you retrieve the
    constants. For example, let's suppose we need to load our configuration from a file:

    .. doctest:: constants

        >>> class Config(Constants):
        ...     PORT = const[int]('port')
        ...     WRONG_TYPE = const[Constants]('port')
        ...     HOST = const[str]('host')
        ...
        ...     def __init__(self):
        ...         self._data = {'host': 'localhost', 'port': '80'}
        ...
        ...     def provide_const(self, name: str, arg: str):
        ...         return self._data[arg]
        ...
        >>> # the actual constant will be auto casted to the type hint if present and
        ... # is one of {str, float, int}. In all cases, the type of the constant value
        ... # is always checked at runtime.
        ... world.get(Config.PORT)
        80
        >>> Config().WRONG_TYPE
        Traceback (most recent call last):
          File "<stdin>", line 1, in ?
        TypeError
        >>> # The type hint is also used as... a type hint !
        ... Config().PORT  # will be treated as an int by Mypy
        80
        >>> world.get(Config.PORT)  # will also be treated as an int by Mypy
        80
        >>> world.get(Config.HOST)
        'localhost'

    In the previous example we're also using the :code:`auto_cast` feature. It provides
    a type hint for Mypy and will be used to cast the result of
    :py:meth:`.Constants.provide_const` if one of :code:`str`, :code:`int` or
    :code:`float`. It can be configured to be either deactivated or extended to support
    enums for example.

    Another useful feature is :code:`default` which simply defines the default value to
    be used if a :py:exc:`LookUpError` is raised in :py:meth:`.Constants.provide_const`.
    It must already have the correct type, :code:`auto_cast` will *not* be applied on it.

    .. doctest:: constants

        >>> class Config(Constants):
        ...     PORT = const[int]('port', default=80)
        ...     HOST = const[str]('host')
        ...
        ...     def __init__(self):
        ...         self._data = {'host': 'localhost'}
        ...
        ...     def provide_const(self, name: str, arg: str):
        ...         return self._data[arg]
        ...
        >>> world.get(Config.PORT)
        80
        >>> world.get(Config.HOST)
        'localhost'

    """

    __slots__ = ()

    @final
    class Conf(FinalImmutable, WithWiringMixin):
        """
        Immutable Constants configuration. To change parameters on a existing instance,
        use either method :py:meth:`.copy` or
        :py:meth:`~.core.wiring.WithWiringMixin.with_wiring`.
        """

        __slots__ = ("wiring", "auto_cast")
        wiring: Optional[Wiring]
        auto_cast: FrozenSet[type]

        def __init__(
            self,
            *,
            auto_cast: Union[Iterable[type], bool] = True,
            wiring: Optional[Wiring] = Wiring(),
        ):
            """
            Args:
                wiring: :py:class:`Wiring` used on the class. Defaults to wire only
                    :code:`__init__()`.
                auto_cast: When the type of the constant is specified with
                    :py:obj:`.const`, the value of the dependency will be cast to its
                    type if it's one of :code:`str`, :code:`float` or :code:`int` by
                    default. You can disable this by specifying code:`auto_cast=False` or
                    change the types for which it's done by specifying explicitly those
                    types.
            """
            if not (wiring is None or isinstance(wiring, Wiring)):
                raise TypeError(f"wiring can be None or a Wiring, but not a {type(wiring)}")

            if isinstance(auto_cast, bool):
                if auto_cast:
                    auto_cast = frozenset((float, int, str))
                else:
                    auto_cast = frozenset()
            elif isinstance(auto_cast, c_abc.Iterable):
                auto_cast = frozenset(auto_cast)
                if not all(isinstance(tpe, type) for tpe in auto_cast):
                    raise TypeError("auto_cast must a boolean or a iterable of types")
            else:
                raise TypeError("auto_cast must a boolean or a iterable of types")

            super().__init__(wiring=wiring, auto_cast=auto_cast)

        def copy(
            self,
            *,
            wiring: Union[Optional[Wiring], Copy] = Copy.IDENTICAL,
            auto_cast: Union[Union[Sequence[type], bool], Copy] = Copy.IDENTICAL,
        ) -> Constants.Conf:
            """
            Copies current configuration and overrides only specified arguments.
            Accepts the same arguments as :code:`__init__`
            """
            return Copy.immutable(self, wiring=wiring, auto_cast=auto_cast)

    __antidote__: ClassVar[Conf] = Conf()

    def provide_const(self, *, name: str, arg: Optional[Any]) -> object:
        """
        Used to retrieve the value of the constant defined with :py:obj:`.const`.
        If a :py:exc:`LookUpError` is raised, the :code:`default` value defined
        with :py:obj:`.const` will be used if any.

        Args:
            name: Name of the constant
            arg: Argument given to :py:obj:`.const` when creating the constant.

        Returns:
            Constant value.
        """
        if arg is None:
            raise ValueError(f"No value provided for const {name}")
        return arg
