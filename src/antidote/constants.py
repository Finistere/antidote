import collections.abc as c_abc
from typing import Callable, cast, FrozenSet, Iterable, Optional, Sequence, Union

from ._compatibility.typing import final
from ._constants import ConstantsMeta, MakeConst
from ._internal import API
from ._internal.utils import Copy, FinalImmutable
from .core.wiring import Wiring, WithWiringMixin

const = MakeConst()


@API.public
class Constants(metaclass=ConstantsMeta, abstract=True):
    """
    Used to declare constants, typically configuration. The purpose is to make common
    configuration manipulation easy. If you need complex operations, consider using the
    Constants class as a service by specifying :code:`public=True`.

    By default all public uppercase attributes are considered to be constants. When using
    them as dependencies or directly through a instance the method :code:`get()` will be
    called with its associated value. Only :code:`__init__()` is wired by default.

    The purpose is to have easily indentify where a specific constant is used in your
    code while keeping it lazy. The class and the constants themselves will only be
    instantiated if necessary.

    .. doctest:: helpers_Constants

        >>> from antidote import Constants, world
        >>> class Config(Constants):
        ...     # By default only public uppercase attributes are considered constants
        ...     DOMAIN = 'domain'
        ...     _A = 'unchanged'
        ...     a = 'unchanged'
        ...
        ...     def __init__(self):
        ...         self._data = {'domain': 'example.com'}
        ...
        ...     # By default the method get() is used to retrieve the constant.
        ...     def get(self, key):
        ...         return self._data[key]
        ...
        >>> Config._A
        'unchanged'
        >>> Config.a
        'unchanged'
        >>> world.get(Config.DOMAIN)
        'example.com'
        >>> # For ease of use, if accessed through an instance, the constant will not
        ... # pass through Antidote.
        ... Config().DOMAIN
        'example.com'

    You may also use :py:func:`.const` if you want to explitly define it as a constant or
    if you want to specify its type. By default if the type is one of :code:`str`,
    :code:`float` or :code:`int`, it will be cast automatically. You can control this
    behavior with the :code:`auto_cast` argument of :py:attr:`~.Constants.Conf`.

    .. doctest:: helpers_Constants_v2

        >>> from antidote import Constants, const, world
        >>> class Config(Constants):
        ...     # As `post` is not uppercase, it would not have been considered to
        ...     # be a constant by default.
        ...     port = const[int]('80')
        ...     port2 = const('8080')
        ...     dummy = const[dict]('dummy')
        ...
        ...     def get(self, value):
        ...         return value
        >>> # Mypy will treat it as a int AND it'll be cast to int.
        ... Config().port
        80
        >>> world.get(Config.port)
        80
        >>> Config().port2
        '8080'
        >>> world.get(Config.port2)
        '8080'
        >>> # Mypy will treat it as a dict but it'll not be cast to anything
        ... Config().dummy
        'dummy'

    You may customize how the Constants class is configured through
    :py:attr:`.__antidote__`.  Among others you can also customize
    :py:attr:`~.Constants.Conf.is_const` used to determine which attributes are constants
    or not.

    .. doctest:: helpers_Constants_v3

        >>> from antidote import Constants, const, world
        >>> class Config(Constants):
        ...     __antidote__ = Constants.Conf(is_const=lambda name: name.startswith("CONF_"))
        ...     CONF_A = "A"
        ...     A = "A"
        ...
        ...     def get(self, value):
        ...         return f"Hello {value}"
        >>> Config().CONF_A
        'Hello A'

    """  # noqa: E501

    @final
    class Conf(FinalImmutable, WithWiringMixin):
        """
        Immutable constants configuration. To change parameters on a existing instance,
        use either method :py:meth:`.copy` or
        :py:meth:`~.core.wiring.WithWiringMixin.with_wiring`.
        """
        __slots__ = ('wiring', 'is_const', 'public', 'auto_cast')
        wiring: Optional[Wiring]
        is_const: Callable[[str], bool]
        public: bool
        auto_cast: FrozenSet[type]

        def __init__(self,
                     *,
                     public: bool = False,
                     is_const: Optional[Callable[[str], bool]] =
                     lambda name: name.isupper() and not name.startswith('_'),
                     auto_cast: Union[Iterable[type], bool] = True,
                     wiring: Optional[Wiring] = Wiring(methods=['__init__'],
                                                       ignore_missing_method=[
                                                           '__init__'])):
            """
            Args:
                public: Whether the Constants instance is available through Antidote like
                    a service or not. Defaults to :py:obj:`False`.
                is_const: Callable determining whether attributes are considered to be
                    constant or not. If :py:obj:`None`, no attributes will be changed.
                    Defaults to changing all public (not starting with an underscore)
                    uppercase attributes.
                wiring: :py:class:`Wiring` used on the class. Defaults to wire only
                    :code:`__init__()`.
                auto_cast: When the type of the constant is specified with
                    :py:func:`.const`, the value of the dependency will be cast to its
                    type if it's one of :code:`str`, :code:`float` or :code:`int` by
                    default. You can disable this by specifying code:`auto_cast=False` or
                    change the types for which it's done by specifying explicitly those
                    types.
            """
            if not isinstance(public, bool):
                raise TypeError(f"public must be a boolean, "
                                f"not a {type(public)}")

            if not (wiring is None or isinstance(wiring, Wiring)):
                raise TypeError(f"wiring can be None or a Wiring, "
                                f"but not a {type(wiring)}")

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

            if is_const is None:
                def is_const(name):
                    return False

            if not callable(is_const):
                raise TypeError(f"is_const must be a callable, not a {type(is_const)}")
            super().__init__(wiring=wiring, is_const=is_const, public=public,
                             auto_cast=auto_cast)

        def copy(self,
                 *,
                 public: Union[bool, Copy] = Copy.IDENTICAL,
                 wiring: Union[Optional[Wiring], Copy] = Copy.IDENTICAL,
                 auto_cast: Union[Union[Sequence[type], bool], Copy] = Copy.IDENTICAL,
                 is_const: Union[Optional[Callable[[str], bool]], Copy] = Copy.IDENTICAL):

            return Constants.Conf(
                public=self.public if public is Copy.IDENTICAL else public,
                wiring=self.wiring if wiring is Copy.IDENTICAL else wiring,
                auto_cast=self.auto_cast if auto_cast is Copy.IDENTICAL else auto_cast,
                # Waiting for a fix: https://github.com/python/mypy/issues/6910
                is_const=(cast(Callable[[str], bool], getattr(self, 'is_const'))
                          if is_const is Copy.IDENTICAL else
                          is_const)
            )

    __antidote__: Conf = Conf()
