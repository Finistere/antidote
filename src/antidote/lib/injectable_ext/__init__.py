from __future__ import annotations

from typing import Callable, Mapping, Optional, overload, Union

from typing_extensions import Literal

from ..._internal import API, Default, retrieve_or_validate_injection_locals
from ..._internal.typing import C
from ...core import Catalog, is_catalog, LifeTime, LifetimeType, TypeHintsLocals, Wiring, world
from ._internal import register_injectable

__all__ = ["antidote_lib_injectable", "injectable"]


@API.public
def antidote_lib_injectable(catalog: Catalog) -> None:
    """
    Adds the necessary for the use of :py:obj:`.injectable` into the specified catalog. The function
    is idempotent, and will not raise an error if it was already applied

    .. doctest:: lib_injectable_extension_include

        >>> from antidote import new_catalog, antidote_lib_injectable
        >>> # Include at catalog creation
        ... catalog = new_catalog(include=[antidote_lib_injectable])
        >>> # Or afterwards
        ... catalog.include(antidote_lib_injectable)

    """
    from ._provider import FactoryProvider

    if FactoryProvider not in catalog.providers:
        catalog.include(FactoryProvider)


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
    Defines the decorated class as a dependency and its associated value to be an instance of it.
    By default, it's a singleto and the class will be instantiated at most once.

    .. doctest:: lib_injectable

        >>> from antidote import injectable, world, inject
        >>> @injectable
        ... class Dummy:
        ...     pass
        >>> world[Dummy]
        <Dummy object at ...>

    By default, it's a singleton and the class will be instantiated at most once and all methods
    are automatically injected:

    .. doctest:: lib_injectable

        >>> world[Dummy] is world[Dummy]
        True
        >>> @injectable
        ... class MyService:
        ...     def __init__(self, dummy: Dummy = inject.me()):
        ...         self.dummy = dummy
        >>> world[MyService].dummy is world[Dummy]
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
        >>> world[ComplexService].env
        'Greetings from build!'

    .. note::

        The registration of the dependency is thread-safe but the wiring isn't.

    .. tip::

        For external classes which you don't own, consider using a :py:obj:`.lazy` function
        instead. Using :py:func:`.injectable` outside the class definition will make it hard to
        track how the dependency was defined and thus less maintainable.

        .. doctest:: lib_injectable

            >>> from antidote import lazy
            >>> class External:
            ...     pass
            >>> @lazy.value(lifetime='singleton')
            ... def external() -> External:
            ...     return External()
            >>> world[external]  # easy to track where and how it's defined
            <External object at ...>

    Args:
        __klass: **/positional-only/** Class to register as a dependency. It will be instantiated
            only when necessary.
        lifetime: Defines how long the dependency value will be cached. Defaults to
            :code:`'singleton'`, the class is instantiated at most once.
        wiring: Defines how and if methods should be injected. By defaults, all methods will be
            injected. Custom injection for specific methods with with :py:obj:`.inject` will not be
            overridden. Specifying :py:obj:`None` will prevent any wiring.
        factory_method: Class or static method to use to build the class. Defaults to
            :py:obj:`None`, the class is instantiated normally.
        type_hints_locals: Local variables to use for :py:func:`typing.get_type_hints`. They
            can be explicitly defined by passing a dictionary or automatically detected with
            :py:mod:`inspect` and frame manipulation by specifying :code:`'auto'`. Specifying
            :py:obj:`None` will deactivate the use of locals. The default behavior depends on the
            :py:data:`.config` value of :py:attr:`~.Config.auto_detect_type_hints_locals`. If
            :py:obj:`True` the default value is equivalent to specifying :code:`'auto'`,
            otherwise to :py:obj:`None`.
        catalog: Defines in which catalog the dependency should be registered. Defaults to
            :py:obj:`.world`.

    """
    if wiring is not None and not isinstance(wiring, Wiring):
        raise TypeError(f"wiring must be a Wiring or None, not a {type(wiring)!r}")
    if not (isinstance(factory_method, str) or factory_method is None):
        raise TypeError(
            f"factory_method must be a class/staticmethod name or None, "
            f"not a {type(factory_method)}"
        )
    if not is_catalog(catalog):
        raise TypeError(f"catalog must be a Catalog, not a {type(catalog)!r}")

    def reg(
        cls: C,
        *,
        lifetime: LifeTime = LifeTime.of(lifetime),
        type_hints_locals: Optional[Mapping[str, object]] = retrieve_or_validate_injection_locals(
            type_hints_locals
        ),
    ) -> C:
        if not isinstance(cls, type):
            raise TypeError(f"@injectable can only be applied on classes, not {type(cls)!r}")

        register_injectable(
            klass=cls,
            lifetime=lifetime,
            wiring=wiring,
            factory_method=factory_method,
            type_hints_locals=type_hints_locals,
            catalog=catalog,
        )
        return cls

    return __klass and reg(__klass) or reg
