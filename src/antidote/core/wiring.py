from __future__ import annotations

import collections.abc as c_abc
import dataclasses
import enum
import warnings
from dataclasses import dataclass
from typing import (Callable, cast, FrozenSet, Iterable, Mapping, Optional, overload, TypeVar,
                    Union)

from typing_extensions import final, Literal

from .injection import AUTO_PROVIDE_TYPE, DEPENDENCIES_TYPE, validate_injection
from .._internal import API
from .._internal.localns import retrieve_or_validate_injection_locals
from .._internal.utils import Copy, Default

C = TypeVar('C', bound=type)
_empty_set: FrozenSet[str] = frozenset()


class Methods(enum.Enum):
    ALL = enum.auto()


@API.public
@final
@dataclass(frozen=True, init=False)
class Wiring:
    """
    Defines how a class should be wired, meaning if/how/which methods are injected. This
    class is intended to be used by configuration objects. If you just want to wire a
    single class, consider using the class decorator :py:func:`.wire` instead. There are
    two purposes:

    - providing a default injection which can be overridden either by changing the wiring
      or using `@inject` when using :code:`attempt_methods`.
    - wiring of multiple methods with similar dependencies.

    Instances are immutable. If you want to change some parameters, typically defaults
    defined by Antidote, you'll need to rely on :py:meth:`~.Wiring.copy`.

    .. doctest:: core_Wiring

        >>> from antidote import Wiring, Service, Provide
        >>> wiring = Wiring(methods=['my_method'])
        >>> class Database(Service):
        ...     pass
        >>> @wiring.wire
        ... class Dummy:
        ...     def my_method(self, db: Provide[Database]) -> Database:
        ...         return db
        >>> Dummy().my_method()
        <Database ...>


    """
    __slots__ = ('methods', 'auto_provide', 'dependencies', 'ignore_type_hints',
                 'raise_on_double_injection')
    methods: Union[Methods, FrozenSet[str]]
    """Method names that must be injected."""
    dependencies: DEPENDENCIES_TYPE
    ignore_type_hints: bool
    auto_provide: API.Deprecated[Union[bool, FrozenSet[type], Callable[[type], bool]]]
    raise_on_double_injection: bool

    def __init__(self,
                 *,
                 methods: Union[Methods, Iterable[str]] = Methods.ALL,
                 dependencies: DEPENDENCIES_TYPE = None,
                 auto_provide: API.Deprecated[AUTO_PROVIDE_TYPE] = None,
                 raise_on_double_injection: bool = False,
                 ignore_type_hints: bool = False) -> None:
        """
        Args:
            methods: Names of methods to be injected. If any of them is already injected,
                an error will be raised. Consider using :code:`attempt_methods` otherwise.
            dependencies: Propagated for every method to :py:func:`.inject`
            auto_provide:
                .. deprecated:: 1.1

                Propagated for every method to :py:func:`.inject`
            ignore_type_hints:
                If :py:obj:`True`, type hints will not be used at all and
                :code:`type_hints_locals`, when calling :py:meth:`~.Wiring.wire`, will
                have no impact.

                .. versionadded:: 1.3

        """
        if not isinstance(raise_on_double_injection, bool):
            raise TypeError(f"raise_on_double_injection must be a boolean, "
                            f"not {type(raise_on_double_injection)}")

        if auto_provide is not None:
            warnings.warn("Using auto_provide is deprecated.", DeprecationWarning)

        if auto_provide is None:
            auto_provide = False
        if isinstance(auto_provide, str) \
                or not (isinstance(auto_provide, (c_abc.Iterable, bool))
                        or callable(auto_provide)):
            raise TypeError(f"auto_provide must be an iterable of method names, "
                            f"not {type(auto_provide)}.")
        if isinstance(auto_provide, c_abc.Iterable):
            auto_provide = frozenset(auto_provide)

        if isinstance(methods, str) or not isinstance(methods, (c_abc.Iterable, Methods)):
            raise TypeError(f"methods must be an iterable of method names, "
                            f"not {type(methods)}.")
        elif isinstance(methods, c_abc.Iterable):
            methods = frozenset(methods)
            if not all(isinstance(method, str) for method in methods):
                raise TypeError("methods is expected to contain methods names (str)")

        if not isinstance(auto_provide, str) and isinstance(auto_provide,
                                                            c_abc.Iterable):
            auto_provide = frozenset(auto_provide)
        validate_injection(dependencies, auto_provide)

        if not isinstance(ignore_type_hints, bool):
            raise TypeError(f"ignore_type_hints must be a boolean, not {type(ignore_type_hints)}")

        object.__setattr__(self, 'methods', methods)
        object.__setattr__(self, 'dependencies', dependencies)
        object.__setattr__(self, 'auto_provide', auto_provide)
        object.__setattr__(self, 'raise_on_double_injection', raise_on_double_injection)
        object.__setattr__(self, 'ignore_type_hints', ignore_type_hints)

    def copy(self,
             *,
             methods: Union[Methods, Iterable[str], Copy] = Copy.IDENTICAL,
             dependencies: Union[DEPENDENCIES_TYPE, Copy] = Copy.IDENTICAL,
             auto_provide: API.Deprecated[Union[AUTO_PROVIDE_TYPE, Copy]] = Copy.IDENTICAL,
             raise_on_double_injection: Union[bool, Copy] = Copy.IDENTICAL,
             ignore_type_hints: Union[bool, Copy] = Copy.IDENTICAL
             ) -> Wiring:
        """
        Copies current wiring and overrides only specified arguments.
        Accepts the same arguments as :py:meth:`~.Wiring.__init__`
        """
        changes: dict[str, object] = {}
        if methods is not Copy.IDENTICAL:
            changes['methods'] = methods
        if dependencies is not Copy.IDENTICAL:
            changes['dependencies'] = dependencies
        if auto_provide is not Copy.IDENTICAL:
            changes['auto_provide'] = auto_provide
        if raise_on_double_injection is not Copy.IDENTICAL:
            changes['raise_on_double_injection'] = raise_on_double_injection
        if ignore_type_hints is not Copy.IDENTICAL:
            changes['ignore_type_hints'] = ignore_type_hints
        return dataclasses.replace(self, **changes)

    @overload
    def wire(self, __klass: C) -> C:
        ...

    @overload
    def wire(self,
             *,
             klass: type,
             type_hints_locals: Optional[Mapping[str, object]] = None,
             class_in_localns: bool = True
             ) -> None:
        ...

    def wire(self,
             __klass: API.Deprecated[Optional[C]] = None,
             *,
             klass: Optional[C] = None,
             type_hints_locals: Optional[Mapping[str, object]] = None,
             class_in_localns: Union[bool, Default] = Default.sentinel
             ) -> Optional[C]:
        """
        Used to wire a class with specified configuration.

        Args:
            __klass: Class to wire. Deprecated, use :code:`klass` instead.
            klass: Class to wire.
            type_hints_locals:
                local variables to use for :py:func:`typing.get_type_hints`.

                .. versionadded:: 1.3

            class_in_localns: Whether to add the current class as a local variable. This
                is typically helpful when the class uses itself as a type hint as during the
                wiring, the class has not yet been defined in the globals/locals. The default
                depends on the value of :code:`ignore_type_hints`. If ignored, the class will not
                be added to the :code:`type_hints_locals`. Specifying :code:`type_hints_locals=None`
                does not prevent the class to be added.

                .. versionadded:: 1.3

        Returns:
            Deprecated: The same class object with specified methods injected.
            It doesn't return anything with the next API.
        """
        from ._wiring import wire_class
        if __klass is not None and not isinstance(__klass, type):
            raise TypeError(f"Expecting a class, got a {type(__klass)}")
        if klass is not None and not isinstance(klass, type):
            raise TypeError(f"Expecting a class, got a {type(klass)}")
        if klass is not None and __klass is not None:
            raise ValueError("Both cls and __klass arguments cannot be used together."
                             "Prefer using cls as __klass is deprecated.")

        cls: C = cast(C, klass or __klass)
        if __klass is None:
            if type_hints_locals is not None:
                if not isinstance(type_hints_locals, dict):
                    raise TypeError(f"type_hints_locals must be None or a dict,"
                                    f"not a {type(type_hints_locals)!r}")
            if class_in_localns is Default.sentinel:
                class_in_localns = not self.ignore_type_hints
            elif not isinstance(class_in_localns, bool):
                raise TypeError(f"class_in_localns must be a boolean if specified, "
                                f"not a {type(class_in_localns)!r}")

            if class_in_localns:
                if self.ignore_type_hints:
                    raise ValueError("class_in_localns cannot be True if ignoring type hints!")
                type_hints_locals = dict(type_hints_locals or {})
                type_hints_locals.setdefault(cls.__name__, cls)

        wire_class(klass=cls, wiring=self, type_hints_locals=type_hints_locals)
        return __klass


@overload
def wire(__klass: C,
         *,
         methods: Union[Methods, Iterable[str]] = Methods.ALL,
         dependencies: DEPENDENCIES_TYPE = None,
         auto_provide: API.Deprecated[AUTO_PROVIDE_TYPE] = None,
         raise_on_double_injection: bool = False,
         ignore_type_hints: bool = False,
         type_hints_locals: Union[
             Mapping[str, object],
             Literal['auto'],
             Default,
             None
         ] = Default.sentinel
         ) -> C:
    ...


@overload
def wire(*,
         methods: Union[Methods, Iterable[str]] = Methods.ALL,
         dependencies: DEPENDENCIES_TYPE = None,
         auto_provide: API.Deprecated[AUTO_PROVIDE_TYPE] = None,
         raise_on_double_injection: bool = False,
         ignore_type_hints: bool = False,
         type_hints_locals: Union[
             Mapping[str, object],
             Literal['auto'],
             Default,
             None
         ] = Default.sentinel
         ) -> Callable[[C], C]:
    ...


@API.public
def wire(
        __klass: Optional[C] = None,
        *,
        methods: Union[Methods, Iterable[str]] = Methods.ALL,
        dependencies: DEPENDENCIES_TYPE = None,
        auto_provide: API.Deprecated[AUTO_PROVIDE_TYPE] = None,
        raise_on_double_injection: bool = False,
        ignore_type_hints: bool = False,
        type_hints_locals: Union[
            Mapping[str, object],
            Literal['auto'],
            Default,
            None
        ] = Default.sentinel
) -> Union[C, Callable[[C], C]]:
    """
    Wire a class by injecting specified methods. This avoids repetition if similar
    dependencies need to be injected in different methods. Methods will only be wrapped
    if and only if Antidote may inject a dependency in it, like :py:func:`.inject`.

    .. doctest:: core_wiring_wire

        >>> from antidote import wire, injectable, inject
        >>> @injectable
        ... class MyService:
        ...     pass
        >>> @wire
        ... class Dummy:
        ...     def method(self, service: MyService = inject.me()) -> MyService:
        ...         return service
        >>> Dummy().method()
        <MyService object at ...>

    Args:
        raise_on_double_injection: Whether an error should be raised if method is already
            injected. Defaults to :py:obj:`False`.
        __klass: Class to wire.
        methods: Names of methods that must be injected. Defaults to all method
        dependencies: Propagated for every method to :py:func:`~.injection.inject`.
        auto_provide:
            .. deprecated:: 1.1

            Propagated for every method to :py:func:`~.injection.inject`.
        ignore_type_hints: If :py:obj:`True`, type hints will not be used at all and
            :code:`type_hints_locals` will have no impact.
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
        Wired class or a class decorator.

    """
    wiring = Wiring(
        methods=methods,
        dependencies=dependencies,
        auto_provide=auto_provide,
        raise_on_double_injection=raise_on_double_injection,
        ignore_type_hints=ignore_type_hints
    )

    if wiring.ignore_type_hints:
        if type_hints_locals is not None and type_hints_locals is not Default.sentinel:
            raise TypeError(f"When ignoring type hints, type_hints_locals MUST be None "
                            f"or not specified at all. Got: {type_hints_locals}")
        localns = None
    else:
        localns = retrieve_or_validate_injection_locals(type_hints_locals)

    def wire_methods(cls: C) -> C:
        wiring.wire(klass=cls, type_hints_locals=localns)
        return cls

    return __klass and wire_methods(__klass) or wire_methods


W = TypeVar('W', bound='WithWiringMixin')


@API.private  # Inheriting this class yourself is not part of the public API
class WithWiringMixin:
    __slots__ = ()

    wiring: Optional[Wiring]

    def copy(self: W, *, wiring: Union[Optional[Wiring], Copy] = Copy.IDENTICAL) -> W:
        raise NotImplementedError()  # pragma: no cover

    @API.public
    def with_wiring(self: W,
                    *,
                    methods: Union[Methods, Iterable[str], Copy] = Copy.IDENTICAL,
                    dependencies: Union[DEPENDENCIES_TYPE, Copy] = Copy.IDENTICAL,
                    auto_provide: API.Deprecated[Union[AUTO_PROVIDE_TYPE, Copy]] = Copy.IDENTICAL,
                    raise_on_double_injection: Union[bool, Copy] = Copy.IDENTICAL,
                    ignore_type_hints: Union[bool, Copy] = Copy.IDENTICAL
                    ) -> W:
        """
        Accepts the same arguments as :py:class:`.Wiring`. Its only purpose is to provide
        a easier way to change the wiring:

        .. code-block:: python

            conf.with_wiring(dependencies={})
            # instead of
            conf.copy(wiring=conf.wiring.copy(dependencies={}))

        """
        if self.wiring is None:
            return self.copy(wiring=Wiring().copy(
                methods=methods,
                dependencies=dependencies,
                auto_provide=auto_provide,
                raise_on_double_injection=raise_on_double_injection,
                ignore_type_hints=ignore_type_hints
            ))
        else:
            return self.copy(wiring=self.wiring.copy(
                methods=methods,
                dependencies=dependencies,
                auto_provide=auto_provide,
                raise_on_double_injection=raise_on_double_injection,
                ignore_type_hints=ignore_type_hints
            ))
