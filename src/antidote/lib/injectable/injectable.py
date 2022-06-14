from __future__ import annotations

from typing import Callable, Mapping, Optional, overload, TypeVar, Union

from typing_extensions import Literal

from ..._internal import API, Default, retrieve_or_validate_injection_locals
from ...core import Catalog, LifeTime, LifetimeType, TypeHintsLocals, Wiring, world
from ._internal import register_injectable

__all__ = ["injectable"]

from ...core.utils import is_catalog

C = TypeVar("C", bound=type)


@overload
def injectable(
    __klass: C,
    *,
    lifetime: LifetimeType = ...,
    wiring: Wiring | None = ...,
    factory_method: str = ...,
    type_hints_locals: TypeHintsLocals = ...,
    catalog: Catalog = ...,
) -> C:
    ...


@overload
def injectable(
    *,
    lifetime: LifetimeType = ...,
    wiring: Wiring | None = ...,
    factory_method: str = ...,
    type_hints_locals: TypeHintsLocals = ...,
    catalog: Catalog = ...,
) -> Callable[[C], C]:
    ...


@API.public
def injectable(
    __klass: Optional[C] = None,
    *,
    lifetime: LifetimeType = "singleton",
    wiring: Optional[Wiring] = Wiring(),
    factory_method: Optional[str] = None,
    type_hints_locals: Union[
        Mapping[str, object], Literal["auto"], Default, None
    ] = Default.sentinel,
    catalog: Catalog = world,
) -> Union[C, Callable[[C], C]]:
    """
    .. versionadded:: 1.3

    Defines the decorated class as a dependency. The class will now point to an instance of it.

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
        >>> world[MyService].dummy
        <Dummy object at ...>

    By default, the singleton :py:class:`.Scope` is used, at most only one instance is created:

    .. doctest:: lib_injectable

        >>> world[MyService] is world[MyService]
        True
        >>> @injectable(lifetime='transient')
        ... class ThrowAwayService:
        ...     pass
        >>> world[ThrowAwayService] is world[ThrowAwayService]
        False

    It is also possible to use a class or static method instead for the intstantiation:

    .. doctest:: lib_injectable

        >>> @injectable(factory_method='build')
        ... class ComplexService:
        ...     def __init__(self, name: str, dummy: Dummy) -> None:
        ...         self.env = name
        ...         self.dummy = dummy
        ...
        ...     @classmethod
        ...     def build(cls, dummy: Dummy = inject.me()) -> 'ComplexService':
        ...         return ComplexService('Greetings from build!', dummy)
        >>> world.get(ComplexService).env
        'Greetings from build!'

    .. note::

        If your wish to declare to register an external class to Antidote, prefer using
        defining a factory with :py:func:`.lazy`.

    Args:
        __klass: **/positional-only/** Class to register as a dependency. It will be instantiated
            only when necessary.
        lifetime: :py:class:`.Scope`, or its lowercase name, if any of the dependency. Defaults to
            :code:`'singleton'`.
        wiring: :py:class:`.Wiring` to be used on the class. By defaults will apply
            a simple :py:func:`.inject` on all methods. But it won't replace any :py:func:`.inject`
            that has been explicitly applied. Specifying :py:obj:`None` will prevent any wiring.
        factory_method: Class or static method to use to build the class. Defaults to
            :py:obj:`None`.
        type_hints_locals: Local variables to use for :py:func:`typing.get_type_hints`. They
            can be explicitly defined by passing a dictionary or automatically detected with
            :py:mod:`inspect` and frame manipulation by specifying :code:`'auto'`. Specifying
            :py:obj:`None` will deactivate the use of locals. When :code:`ignore_type_hints` is
            :py:obj:`True`, this features cannot be used. The default behavior depends on the
            :py:data:`.config` value of :py:attr:`~.Config.auto_detect_type_hints_locals`. If
            :py:obj:`True` the default value is equivalent to specifying :code:`'auto'`,
            otherwise to :py:obj:`None`.
        catalog: :py:class:`.Catalog` in which the dependency should be registered. Defaults to
            :py:obj:`.world`

    """
    valid_lifetime = LifeTime.of(lifetime)
    if wiring is not None and not isinstance(wiring, Wiring):
        raise TypeError(f"wiring must be a Wiring or None, not a {type(wiring)!r}")
    if not (isinstance(factory_method, str) or factory_method is None):
        raise TypeError(
            f"factory_method must be a class/staticmethod name or None, "
            f"not a {type(factory_method)}"
        )
    if not is_catalog(catalog):
        raise TypeError(f"catalog must be a Catalog, not a {type(catalog)!r}")

    tp_locals = retrieve_or_validate_injection_locals(type_hints_locals)

    def reg(cls: C) -> C:
        if not isinstance(cls, type):
            raise TypeError(f"@injectable can only be applied on classes, not {type(cls)!r}")

        register_injectable(
            klass=cls,
            lifetime=valid_lifetime,
            wiring=wiring,
            factory_method=factory_method,
            type_hints_locals=tp_locals,
            catalog=catalog,
        )
        return cls

    return __klass and reg(__klass) or reg
