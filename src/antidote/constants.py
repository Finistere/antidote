from typing import Callable, Optional, Union

from ._compatibility.typing import final
from ._constants import ConstantsMeta, MakeConst
from ._internal import API
from ._internal.utils import Copy, FinalImmutable
from .core.wiring import Wiring, WithWiringMixin

const = MakeConst()


@API.public
class Constants(metaclass=ConstantsMeta, abstract=True):
    """
    Used to declare constants, typically configuration. By default all public uppercase
    attributes are considered to be constants. When using them as dependencies or directly
    through a instance the method :code:`get()` will be called with its associated value.
    Only :code:`__init__()` is wired by default.

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
    if you want to specify its type.

    .. doctest:: helpers_Constants_v2

        >>> from antidote import Constants, const, world
        >>> class Config(Constants):
        ...     _PORT = const[int]('80')
        ...     _PORT2 = const('8080')
        ...
        ...     def get(self, value):
        ...         return int(value)
        >>> # Mypy will treat it as a int
        ... Config()._PORT
        80

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
        __slots__ = ('wiring', 'is_const', 'public')
        wiring: Optional[Wiring]
        is_const: Optional[Callable[[str], bool]]
        public: bool

        def __init__(self,
                     *,
                     public: bool = False,
                     is_const: Optional[Callable[[str], bool]] =
                     lambda name: name.isupper() and not name.startswith('_'),
                     wiring: Optional[Wiring] = Wiring(methods=['__init__', 'get'],
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
            """
            if not isinstance(public, bool):
                raise TypeError(f"public must be a boolean, "
                                f"not a {type(public)}")

            if not (wiring is None or isinstance(wiring, Wiring)):
                raise TypeError(f"wiring can be None or a Wiring, "
                                f"but not a {type(wiring)}")

            if is_const is None:
                def is_const(name):
                    return False

            if not callable(is_const):
                raise TypeError(f"is_const must be a callable, not a {type(is_const)}")
            super().__init__(wiring=wiring, is_const=is_const, public=public)

        def copy(self,
                 *,
                 public: Union[bool, Copy] = Copy.IDENTICAL,
                 wiring: Union[Optional[Wiring], Copy] = Copy.IDENTICAL,
                 is_const: Union[Callable[[str], bool], Copy] = Copy.IDENTICAL):
            return Constants.Conf(
                public=self.public if public is Copy.IDENTICAL else public,
                wiring=self.wiring if wiring is Copy.IDENTICAL else wiring,
                is_const=self.is_const if is_const is Copy.IDENTICAL else is_const
            )

    __antidote__: Conf = Conf()
