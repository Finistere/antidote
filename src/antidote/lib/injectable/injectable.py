from __future__ import annotations

from typing import Callable, Mapping, Optional, overload, TypeVar, Union

from typing_extensions import Literal

from ._internal import register_injectable
from ..._internal import API
from ..._internal.localns import retrieve_or_validate_injection_locals
from ..._internal.utils import Default
from ...core import Scope, Wiring
from ...utils import validated_scope

__all__ = ["injectable"]

C = TypeVar("C", bound=type)


@overload
def injectable(
    klass: C,
    *,
    singleton: Optional[bool] = None,
    scope: Optional[Scope] = Scope.sentinel(),
    wiring: Optional[Wiring] = Wiring(),
    factory_method: Optional[str] = None,
    type_hints_locals: Union[
        Mapping[str, object], Literal["auto"], Default, None
    ] = Default.sentinel,
) -> C:
    ...


@overload
def injectable(
    *,
    singleton: Optional[bool] = None,
    scope: Optional[Scope] = Scope.sentinel(),
    wiring: Optional[Wiring] = Wiring(),
    factory_method: Optional[str] = None,
    type_hints_locals: Union[
        Mapping[str, object], Literal["auto"], Default, None
    ] = Default.sentinel,
) -> Callable[[C], C]:
    ...


@API.public
def injectable(
    klass: Optional[C] = None,
    *,
    singleton: Optional[bool] = None,
    scope: Optional[Scope] = Scope.sentinel(),
    wiring: Optional[Wiring] = Wiring(),
    factory_method: Optional[str] = None,
    type_hints_locals: Union[
        Mapping[str, object], Literal["auto"], Default, None
    ] = Default.sentinel,
) -> Union[C, Callable[[C], C]]:
    """
    .. versionadded:: 1.3

    Defines the decorated class as an injectable.

    .. doctest:: lib_injectable

        >>> from antidote import injectable
        >>> @injectable
        ... class Dummy:
        ...     pass

    All methods of the classe are automatically injected by default:

    .. doctest:: lib_injectable

        >>> from antidote import world, inject
        >>> @injectable
        ... class MyService:
        ...     def __init__(self, dummy: Dummy = inject.me()):
        ...         self.dummy = dummy
        >>> world.get(MyService).dummy
        <Dummy object at ...>

    By default all injectables are declared as singleton, meaning only one instances will be used
    during the application lifetime. But you can configure it however you need it:

    .. doctest:: lib_injectable

        >>> world.get(MyService) is world.get(MyService)
        True
        >>> @injectable(singleton=False)
        ... class ThrowAwayService:
        ...     pass
        >>> world.get(ThrowAwayService) is world.get(ThrowAwayService)
        False

    One can also specify a :code:`factory_method` instead of relying only on :code:`__init__`.

    .. doctest:: lib_injectable

        >>> @injectable(factory_method='build')
        ... class ComplexService:
        ...     def __init__(self, name: str, dummy: Dummy) -> None:
        ...         self.name = name
        ...         self.dummy = dummy
        ...
        ...     @classmethod
        ...     def build(cls, dummy: Dummy = inject.me()) -> 'ComplexService':
        ...         return ComplexService('Greetings from build!', dummy)
        >>> world.get(ComplexService).name
        'Greetings from build!'

    .. note::

        If your wish to declare to register an external class to Antidote, prefer using
        a factory with :py:func:`~.factory.factory`.

    Args:
        klass: Class to register as a dependency. It will be instantiated  only when
            requested.
        singleton: Whether the injectable is a singleton or not. A singleton is instantiated only
            once. Mutually exclusive with :code:`scope`. Defaults to :py:obj:`True`
        scope: Scope of the service. Mutually exclusive with :code:`singleton`.  The scope defines
            if and how long the service will be cached. See :py:class:`~.core.container.Scope`.
            Defaults to :py:meth:`~.core.container.Scope.singleton`.
        wiring: :py:class:`.Wiring` to be used on the class. By defaults will apply
            a simple :py:func:`.inject` on all methods, so only annotated type hints are
            taken into account. Can be deactivated by specifying :py:obj:`None`.
        factory_method: Class or static method to use to build the class. Defaults to
            :py:obj:`None`.

            .. versionadded:: 1.3
        type_hints_locals: Local variables to use for :py:func:`typing.get_type_hints`. They
            can be explicitly defined by passing a dictionary or automatically detected with
            :py:mod:`inspect` and frame manipulation by specifying :code:`'auto'`. Specifying
            :py:obj:`None` will deactivate the use of locals. When :code:`ignore_type_hints` is
            :py:obj:`True`, this features cannot be used. The default behavior depends on the
            :py:data:`.config` value of :py:attr:`~.Config.auto_detect_type_hints_locals`. If
            :py:obj:`True` the default value is equivalent to specifying :code:`'auto'`,
            otherwise to :py:obj:`None`.

            .. versionadded:: 1.3

    Returns:
        The decorated class, unmodified, if specified or the class decorator.

    """
    scope = validated_scope(scope, singleton, default=Scope.singleton())
    if wiring is not None and not isinstance(wiring, Wiring):
        raise TypeError(f"wiring must be a Wiring or None, not a {type(wiring)!r}")
    if not (isinstance(factory_method, str) or factory_method is None):
        raise TypeError(
            f"factory_method must be a class/staticmethod name or None, "
            f"not a {type(factory_method)}"
        )

    localns = retrieve_or_validate_injection_locals(type_hints_locals)

    def reg(cls: C) -> C:
        if not isinstance(cls, type):
            raise TypeError(f"@injectable can only be applied on classes, not {type(cls)!r}")

        register_injectable(
            klass=cls,
            scope=scope,
            wiring=wiring,
            factory_method=factory_method,
            type_hints_locals=localns,
        )
        return cls

    return klass and reg(klass) or reg
